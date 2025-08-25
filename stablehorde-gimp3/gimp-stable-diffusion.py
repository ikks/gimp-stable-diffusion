#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Gimp3 plugin for AiHorde
# Authors:
#  * blueturtleai <https://github.com/blueturtleai> Original
#  * binarymass <https://github.com/binarymass>
#  * Igor Támara <https://github.com/ikks>
#
#
# MIT lICENSE
# https://github.com/ikks/gimp-stable-diffusion/blob/main/LICENSE


import base64
import getpass
import gi
import logging
import os
import platform
import sys
import tempfile

from pathlib import Path
from typing import Union

gi.require_version("Gimp", "3.0")
from gi.repository import Gimp  # noqa: E402

gi.require_version("GimpUi", "3.0")
from gi.repository import GimpUi  # noqa: E402

gi.require_version("Gegl", "0.4")
from gi.repository import Gegl  # noqa: E402
from gi.repository import Gio  # noqa: E402
from gi.repository import GLib  # noqa: E402
from gi.repository import GObject  # noqa: E402
from gi.repository import Gtk  # noqa: E402

import_message_error = None

DEBUG = True

LOGGING_LEVEL = logging.DEBUG

log_file = os.path.join(tempfile.gettempdir(), "gimp-stable-diffusion.log")
logging.basicConfig(
    filename=log_file,
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

try:
    expected_dir = Path(Gimp.directory()) / "plug-ins" / "gimp-stable-diffusion"
    submodule_path = expected_dir / "module"
    sys.path.append(str(submodule_path))
    from aihordeclient import (
        ANONYMOUS_KEY,
        MAX_HEIGHT,
        MAX_MP,
        MAX_WIDTH,
        MIN_HEIGHT,
        MIN_WIDTH,
        MODELS,
        INPAINT_MODELS,
    )
    from aihordeclient import (
        log_exception,
        AiHordeClient,
        InformerFrontend,
        HordeClientSettings,
        ProcedureInformation,
    )
except ModuleNotFoundError as ex:
    import_message_error = "Make sure the plug-in is installed in {} ".format(
        expected_dir
    )
    raise ex
except Exception as ex:
    raise ex

VERSION = "3.3"

METADATA_FOR_GIMP = '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<metadata>\n  <tag name="Exif.GPSInfo.GPSAltitude">0/100</tag>\n  <tag name="Exif.Image.Artist">{user}</tag>\n  <tag name="Exif.Image.BitsPerSample">8 8 8</tag>\n  <tag name="Exif.Image.Copyright">AI Generated, trained with {model_name}</tag>\n  <tag name="Exif.Image.DateTime">2025:08:21 22:02:26</tag>\n  <tag name="Exif.Image.ExifTag">330</tag>\n  <tag name="Exif.Image.GPSTag">348</tag>\n  <tag name="Exif.Image.ImageDescription">{lines_properties}</tag>\n  <tag name="Exif.Image.ImageLength">384</tag>\n  <tag name="Exif.Image.ImageWidth">512</tag>\n  <tag name="Exif.Image.Orientation">1</tag>\n  <tag name="Exif.Image.ResolutionUnit">3</tag>\n  <tag name="Exif.Image.Software">GIMP 3.0.4</tag>\n  <tag name="Exif.Image.XResolution">10748/91</tag>\n  <tag name="Exif.Image.YResolution">10748/91</tag>\n  <tag name="Exif.Photo.ColorSpace">1</tag>\n  <tag name="Exif.Thumbnail.BitsPerSample">8 8 8</tag>\n  <tag name="Exif.Thumbnail.Compression">6</tag>\n  <tag name="Exif.Thumbnail.ImageLength">192</tag>\n  <tag name="Exif.Thumbnail.ImageWidth">256</tag>\n  <tag name="Exif.Thumbnail.JPEGInterchangeFormat">494</tag>\n  <tag name="Exif.Thumbnail.JPEGInterchangeFormatLength">8539</tag>\n  <tag name="Exif.Thumbnail.NewSubfileType">1</tag>\n  <tag name="Exif.Thumbnail.PhotometricInterpretation">6</tag>\n  <tag name="Exif.Thumbnail.SamplesPerPixel">3</tag>\n  <namespace prefix="DICOM" url="http://ns.adobe.com/DICOM/"></namespace>\n  <tag name="Xmp.DICOM.PatientSex">female</tag>\n  <namespace prefix="GIMP" url="http://www.gimp.org/xmp/"></namespace>\n  <tag name="Xmp.GIMP.API">3.0</tag>\n  <tag name="Xmp.GIMP.Platform">Linux</tag>\n  <tag name="Xmp.GIMP.TimeStamp">1755831790611856</tag>\n  <tag name="Xmp.GIMP.Version">3.0.4</tag>\n  <namespace prefix="dc" url="http://purl.org/dc/elements/1.1/"></namespace>\n  <tag name="Xmp.dc.Format">image/png</tag>\n  <tag name="Xmp.dc.creator">{user}</tag>\n  <tag name="Xmp.dc.description">lang=&quot;x-default&quot; {lines_properties}</tag>\n  <tag name="Xmp.dc.rights">lang=&quot;x-default&quot; AI Generated</tag>\n  <tag name="Xmp.dc.subject">AI Generated; {model_name}; {plugin_name}</tag>\n  <tag name="Xmp.dc.title">lang=&quot;x-default&quot; {prompt}</tag>\n  <namespace prefix="iptc" url="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"></namespace>\n  <tag name="Xmp.iptc.CiUrlWork">https://aihorde.net</tag>\n  <namespace prefix="Iptc4xmpCore" url="http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"></namespace>\n  <tag name="Xmp.iptc.CreatorContactInfo/Iptc4xmpCore:CiUrlWork">https://aihorde.net</tag>\n  <namespace prefix="photoshop" url="http://ns.adobe.com/photoshop/1.0/"></namespace>\n  <tag name="Xmp.photoshop.AuthorsPosition">{prompt} by {model_name}</tag>\n  <tag name="Xmp.photoshop.CaptionWriter">{plugin_name} {plugin_version}</tag>\n  <tag name="Xmp.photoshop.Category">AI generated</tag>\n  <tag name="Xmp.photoshop.SupplementalCategories">{model_name}</tag>\n  <namespace prefix="tiff" url="http://ns.adobe.com/tiff/1.0/"></namespace>\n  <tag name="Xmp.tiff.Orientation">1</tag>\n  <namespace prefix="xmp" url="http://ns.adobe.com/xap/1.0/"></namespace>\n  <tag name="Xmp.xmp.CreatorTool">GIMP</tag>\n  <tag name="Xmp.xmp.MetadataDate">2025:08:21T22:02:26-05:00</tag>\n  <tag name="Xmp.xmp.ModifyDate">2025:08:21T22:02:26-05:00</tag>\n  <namespace prefix="xmpMM" url="http://ns.adobe.com/xap/1.0/mm/"></namespace>\n  <tag name="Xmp.xmpMM.DocumentID">gimp:docid:gimp:6ca2d23c-d9f4-48a7-92ba-4708c927aa67</tag>\n  <namespace prefix="stEvt" url="http://ns.adobe.com/xap/1.0/sType/ResourceEvent#"></namespace>\n  <tag name="Xmp.xmpMM.History[1]/stEvt:action">saved</tag>\n  <tag name="Xmp.xmpMM.History[1]/stEvt:changed">/metadata</tag>\n  <tag name="Xmp.xmpMM.History[1]/stEvt:instanceID">xmp.iid:9653e42d-8f45-4a47-a7b9-0c2efa4d2333</tag>\n  <tag name="Xmp.xmpMM.History[1]/stEvt:softwareAgent">GIMP 3.0.4 (Linux)</tag>\n  <tag name="Xmp.xmpMM.History[1]/stEvt:when">2025-08-21T22:01:52-05:00</tag>\n  <tag name="Xmp.xmpMM.History[2]/stEvt:action">saved</tag>\n  <tag name="Xmp.xmpMM.History[2]/stEvt:changed">/</tag>\n  <tag name="Xmp.xmpMM.History[2]/stEvt:instanceID">xmp.iid:9b95539b-cd16-43d3-8b88-18669aef2c34</tag>\n  <tag name="Xmp.xmpMM.History[2]/stEvt:softwareAgent">GIMP 3.0.4 (Linux)</tag>\n  <tag name="Xmp.xmpMM.History[2]/stEvt:when">2025-08-21T22:03:10-05:00</tag>\n  <tag name="Xmp.xmpMM.History[3]/stEvt:action">saved</tag>\n  <tag name="Xmp.xmpMM.History[3]/stEvt:changed">/metadata</tag>\n  <tag name="Xmp.xmpMM.History[3]/stEvt:instanceID">xmp.iid:57ee7bb5-1065-4a9f-8a8b-741f345b7f22</tag>\n  <tag name="Xmp.xmpMM.History[3]/stEvt:softwareAgent">GIMP 3.0.4 (Linux)</tag>\n  <tag name="Xmp.xmpMM.History[3]/stEvt:when">2025-08-22T00:07:07-05:00</tag>\n  <tag name="Xmp.xmpMM.InstanceID">xmp.iid:b2eda0c9-92af-4656-8f09-1d6232159b0e</tag>\n  <tag name="Xmp.xmpMM.OriginalDocumentID">xmp.did:e91842a7-0bbd-4853-9a81-cb0113e4a48a</tag>\n  <namespace prefix="xmpRights" url="http://ns.adobe.com/xap/1.0/rights/"></namespace>\n  <tag name="Xmp.xmpRights.Marked">False</tag>\n  <tag name="Iptc.Application2.Byline">{user}</tag>\n  <tag name="Iptc.Application2.BylineTitle">{prompt} by {model_name}</tag>\n  <tag name="Iptc.Application2.Caption">{lines_properties}</tag>\n  <tag name="Iptc.Application2.Category">AI generated</tag>\n  <tag name="Iptc.Application2.Copyright">AI Generated, trained with {model_name}</tag>\n  <tag name="Iptc.Application2.Keywords">AI Generated; {model_name}; {plugin_name}</tag>\n  <tag name="Iptc.Application2.ObjectName">{prompt}</tag>\n  <tag name="Iptc.Application2.SuppCategory">{model_name}</tag>\n  <tag name="Iptc.Application2.Writer">{plugin_name} {plugin_version}</tag>\n</metadata>\n'

HELP_URL = "https://aihorde.net/faq"
"""
Help url for the extension
"""

URL_VERSION_UPDATE = "https://raw.githubusercontent.com/ikks/gimp-stable-diffusion/main/stablehorde/version.json"
"""
Latest version for the extension
"""

PROPERTY_CURRENT_SESSION = "py3-stablehorde-checked-update"

URL_DOWNLOAD = "https://github.com/ikks/gimp-stable-diffusion/releases"
"""
Download URL for gimp-stable-diffusion
"""

HORDE_CLIENT_NAME = "AiHordeForGimp"
"""
Name of the client sent to API
"""

PLUGIN_DESCRIPTION = """Stable Diffusion mixes are powered by https://aihorde.net/ ,
join, get an API key, earn kudos and create more.  You need Internet to make use
of this plugin.  You can use the power of other GPUs worlwide and help with yours
aswell.  An AI plugin for Gimp that just works. This plugin requires Python3.9

For example, make use of a prompt like:
  a highly detailed epic cinematic concept art CG render digital painting
  artwork: dieselpunk warship with cannons and radar navigating through waves
  in the ocean. By Greg Rutkowski,
  Ilya Kuvshinov, WLOP, Stanley Artgerm Lau, Ruan Jia and Fenghua Zhong,
  trending on ArtStation, subtle muted cinematic colors, made in Maya, Blender
  and Photoshop, octane render, excellent composition, cinematic atmosphere,
  dynamic dramatic cinematic lighting, precise correct anatomy, aesthetic,
  very inspirational, arthouse.
"""

INIT_FILE = "init.png"
GENERATED_FILE = "stablehorde-generated.png"

init_file = r"{}".format(os.path.join(tempfile.gettempdir(), INIT_FILE))
generated_file = r"{}".format(os.path.join(tempfile.gettempdir(), GENERATED_FILE))


# Localization helpers
def _(message):
    return GLib.dgettext(None, message)


class StableDiffusion(Gimp.PlugIn):
    plug_in_proc_t2i = "ikks-py3-stablehorde-t2i"
    plug_in_proc_i2i = "ikks-py3-stablehorde-i2i"
    plug_in_proc_inpaint = "ikks-py3-stablehorde-inpaint"
    plug_in_binary = "py3-stablehorde"

    def __init__(self, *args, **kwargs):
        self.t2i = ProcedureInformation(
            model_choices=MODELS,
            action="MODE_TEXT2IMG",
            cache_key="models",
            default_model="stable_diffusion",
        )
        self.i2i = ProcedureInformation(
            model_choices=MODELS,
            action="MODE_IMG2IMG",
            cache_key="models",
            default_model="stable_diffusion",
        )
        self.in_paint = ProcedureInformation(
            model_choices=INPAINT_MODELS,
            action="MODE_INPAINTING",
            cache_key="inpainting",
            default_model="stable_diffusion_inpainting",
        )

        self.procedures = {
            self.plug_in_proc_t2i: self.t2i,
            self.plug_in_proc_i2i: self.i2i,
            self.plug_in_proc_inpaint: self.in_paint,
        }
        self.plug_in_procs = list(self.procedures.keys())
        if DEBUG:
            print(f"Your log is at {log_file}")
        super().__init__(*args, **kwargs)

    def do_query_procedures(self) -> list[str]:
        """
        Returns the list of available procedures:
        * TXT2IMG
        * IMG2IMG
        * INPAINT
        """
        return self.plug_in_procs

    def do_create_procedure(self, name: str):
        """
        Creates the procedure according to the name, currently
        * TXT2IMG
        * IMG2IMG
        * INPAINT

        """
        procedure = None
        self.check_counter = 0
        self.check_max = None
        logging.debug(name)
        logging.debug(self.plug_in_procs)
        if name not in self.plug_in_procs:
            return procedure

        self.st_manager = HordeClientSettings(
            Path(Gimp.cache_directory()) / "ikks-py3-stablehorde"
        )
        self.procedures[name].update_choices_from(self.st_manager.load())
        # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
        self.t2i.menu_label = _("_Text to Image")
        # TRANSLATORS: Dialog title
        self.t2i.dialog_title = _("TXT2IMG") + " - " + VERSION
        self.t2i.dialog_description = _("Generate an image from a text") + "\n"
        # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
        self.i2i.menu_label = _("_Image to Image")
        # TRANSLATORS: Dialog title
        self.i2i.dialog_title = _("IMG2IMG") + " - " + VERSION
        self.i2i.dialog_description = (
            _("Generate a variation of the current image") + "\n"
        )
        # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
        self.in_paint.menu_label = _("Inpainting") + " - " + VERSION
        # TRANSLATORS: Dialog title
        self.in_paint.dialog_title = _("Inpaint Region")
        self.in_paint.dialog_description = (
            _("Replace transparent portion of the image") + "\n"
        )
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, self.run, None
        )
        if name == self.plug_in_proc_t2i:
            procedure.set_sensitivity_mask(
                Gimp.ProcedureSensitivityMask.DRAWABLE
                | Gimp.ProcedureSensitivityMask.NO_DRAWABLES
                | Gimp.ProcedureSensitivityMask.NO_IMAGE
            )
        else:
            procedure.set_sensitivity_mask(
                Gimp.ProcedureSensitivityMask.DRAWABLE
                | Gimp.ProcedureSensitivityMask.NO_DRAWABLES
            )
        procedure.set_menu_label(self.procedures[name].menu_label)
        procedure.set_attribution("ikks", "Igor Támara", "2025")
        procedure.add_menu_path("<Image>/AI/AI _Horde")
        procedure.set_documentation(
            self.procedures[name].dialog_description,
            PLUGIN_DESCRIPTION,
            None,
        )
        procedure.add_int_argument(
            "width",
            _("W_idth"),
            _(f"Height X Width can be at most 2048x2048={MAX_MP} pixels"),
            MIN_WIDTH,
            MAX_WIDTH,
            512,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "height",
            _("Height"),
            _(f"Height X Width can be at most 2048x2048={MAX_MP} pixels"),
            MIN_HEIGHT,
            MAX_HEIGHT,
            384,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_string_argument(
            "prompt-type",
            _("Action to execute"),
            None,
            self.procedures[name].action,
            GObject.ParamFlags.READWRITE,
        )

        model_choices = Gimp.Choice.new()

        for i, model_name in enumerate(self.procedures[name].model_choices):
            model_choices.add(model_name, i, model_name.capitalize(), "")
        initial_selection = self.procedures[name].model_choices[0]

        procedure.add_choice_argument(
            "model",
            _("_Model to apply"),
            None,
            model_choices,
            initial_selection,
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_double_argument(
            "init-strength",
            _("_Denoising"),
            _(
                "How much of the original image to convert to noise and regenerate. The higher you set this, the more the image changes"
            ),
            0.0,
            1.0,
            0.3,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_double_argument(
            "prompt-strength",
            _("Prompt Stre_ngth (CFG)"),
            _(
                "How strongly the AI follows the prompt vs how much creativity to allow it. Set to 1 for Flux, use 2-4 for LCM and lightning, 5-7 is common for SDXL models, 6-9 is common for sd15"
            ),
            0,
            20,
            8,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "steps",
            _("S_teps"),
            _(
                "How many sampling steps to perform for generation. Should generally be at least double the CFG unless using a second-order or higher sampler (anything with dpmpp is second order)"
            ),
            10,
            150,
            27,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "nimages",
            _("Image Count"),
            _("Number of images to generate"),
            1,
            10,
            1,
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_string_argument(
            "seed",
            _("S_eed (optional)"),
            _(
                "Set a seed to regenerate (reproducible), or it'll be chosen at random by the worker"
            ),
            "",
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_string_argument(
            "prompt",
            _("_Prompt"),
            _(
                "Let your imagination run wild or put a proper description of your desired output. Use full grammar for Flux, use tag-like language for sd15, use short phrases for sdxl. Pony, Noob, Illustrious are SDXL with strong understanding of booru tags"
            ),
            "Draw a beautiful...",
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "nsfw",
            _("NSF_W"),
            _(
                "Whether or not your image is intended to be NSFW. May reduce generation speed (workers can choose if they wish to take nsfw requests)"
            ),
            False,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "censor-nsfw",
            _("Censor NS_FW"),
            _(
                "Separate from the NSFW flag, should workers return nsfw images. Censorship is implemented to be safe and overcensor rather than risk returning unwanted NSFW"
            ),
            False,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_string_argument(
            "api-key",
            _("API _key (optional)"),
            _(
                "Get yours at https://aihorde.net/ for free. Recommended: Anonymous users are last in the queue"
            ),
            "",
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "max-wait-minutes",
            _("Max Wait (in min_utes)"),
            _(
                "How long to wait for your generation to complete. Depends on number of workers and user priority (more kudos = more priority. Anonymous users are last)"
            ),
            1,
            45,
            8,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "debug",
            _("_Debug"),
            _(
                "Allow to see the Debug messages, launch Gimp from a terminal, cmd to see the place where the logging is shown"
            ),
            DEBUG,
            GObject.ParamFlags.READWRITE,
        )
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        procedure_name = procedure.get_name()
        created_image = False
        if image is None and procedure_name in [
            self.plug_in_proc_i2i,
            self.plug_in_proc_inpaint,
        ]:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(f"'{procedure_name}' requires an image."),
            )
        if len(drawables) > 1:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(
                    f"Procedure '{procedure_name}' works with zero or one layer."
                ),
            )
        elif len(drawables) == 1:
            if not isinstance(drawables[0], Gimp.Layer):
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(f"Procedure '{procedure_name}' works with layers only."),
                )

        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init(self.plug_in_binary)

            dialog = GimpUi.ProcedureDialog.new(
                procedure,
                config,
                f"AI Horde - { self.procedures[procedure_name].dialog_title }",
            )
            dialog.get_widget("prompt-strength", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("nimages", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("init-strength", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("steps", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("max-wait-minutes", GimpUi.SpinScale.__gtype__)
            ctrl = dialog.get_widget("width", GimpUi.LabelSpin.__gtype__)
            ctrl.set_increments(64, 128)
            ctrl = dialog.get_widget("height", GimpUi.LabelSpin.__gtype__)
            ctrl.set_increments(64, 128)

            dialog.get_label(
                "header-text",
                self.procedures[procedure_name].dialog_description,
                True,
                False,
            )
            controls_to_show = ["header-text", "prompt"]
            if procedure_name == self.plug_in_proc_t2i:
                box = dialog.fill_flowbox("size-box", ["width", "height"])
                box.set_orientation(Gtk.Orientation.HORIZONTAL)
                controls_to_show.extend(["size-box"])
            controls_to_show.extend(
                [
                    "model",
                    "prompt-strength",
                ]
            )
            if procedure_name == self.plug_in_proc_i2i:
                controls_to_show.append("init-strength")
            if procedure_name in [self.plug_in_proc_i2i, self.plug_in_proc_inpaint]:
                controls_to_show.append("nimages")

            controls_to_show.extend(
                [
                    "steps",
                    "nsfw",
                    "censor-nsfw",
                    "max-wait-minutes",
                    "seed",
                    "api-key",
                    "debug",
                ]
            )
            dialog.fill(controls_to_show)
            if not dialog.run():
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
            dialog.destroy()
        global DEBUG
        DEBUG = config.get_property("debug")
        if DEBUG:
            print(f"Your log is at {log_file}")

        prompt = config.get_property("prompt")
        if prompt == "":
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_("Please enter a prompt.")),
            )

        source_image = ""
        if image is not None:
            source_image = self.get_image_data(image)
        elif procedure_name == self.plug_in_proc_t2i:
            width = config.get_property("width")
            height = config.get_property("height")

            if (
                width < MIN_WIDTH
                or width > MAX_WIDTH
                or height < MIN_HEIGHT
                or height > MAX_HEIGHT
            ):
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(
                        _("The length of each side must be between {} and {}").format(
                            MIN_WIDTH, MAX_HEIGHT
                        )
                    ),
                )
            if width * height > MAX_MP:
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(
                        _(
                            "Please resize your image to make sure width * height is lower than 4MP ({})"
                        ).format(MAX_MP)
                    ),
                )
            image = Gimp.Image.new(width, height, Gimp.ImageBaseType.RGB)
            layer = Gimp.Layer.new(
                image,
                "background",
                width,
                height,
                Gimp.ImageBaseType.RGB,
                0.0,
                Gimp.LayerMode.NORMAL,
            )
            image.insert_layer(layer, None, 0)
            drawables = [layer]
            Gimp.Display.new(image)
            created_image = True

        model = config.get_property("model")
        mode = config.get_property("prompt-type")
        init_strength = config.get_property("init-strength")
        prompt_strength = config.get_property("prompt-strength")
        steps = config.get_property("steps")
        nsfw = config.get_property("nsfw")
        censor_nsfw = config.get_property("censor-nsfw")
        api_key = config.get_property("api-key") or ANONYMOUS_KEY
        max_wait_minutes = config.get_property("max-wait-minutes")
        seed = config.get_property("seed")
        nimages = config.get_property("nimages")
        image_width = image.get_width()
        image_height = image.get_height()
        if (
            image_width < MIN_WIDTH
            or image_width > MAX_WIDTH
            or image_height < MIN_HEIGHT
            or image_height > MAX_HEIGHT
        ):
            if created_image:
                image.delete()
                Gimp.displays_flush()
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(
                    _("The length of each side must be between {} and {}").format(
                        MIN_WIDTH, MAX_HEIGHT
                    )
                ),
            )
        if image_width * image_height > MAX_MP:
            if created_image:
                image.delete()
                Gimp.displays_flush()
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(
                    _(
                        "Please resize your image to make sure width * height is lower than 4MP ({})"
                    ).format(MAX_MP)
                ),
            )

        if mode == "MODE_INPAINTING" and drawables[0].has_alpha == 0:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_("When inpainting, the image must have an alpha channel.")),
            )

        options = {
            "model": model,
            "mode": mode,
            "init_strength": init_strength,
            "prompt_strength": prompt_strength,
            "steps": steps,
            "nsfw": nsfw,
            "censor_nsfw": censor_nsfw,
            "api_key": api_key,
            "max_wait_minutes": max_wait_minutes,
            "seed": seed,
            "nimages": nimages,
            "image_width": image_width,
            "image_height": image_height,
            "prompt": prompt,
            "source_image": source_image,
            "default_model": self.procedures[procedure_name].default_model,
        }
        options["local_settings"] = {
            "models": self.procedures[procedure_name].model_choices,
            "date_refreshed_models": self.procedures[procedure_name].refreshed_date,
        }

        self.bridge: GimpUtilitiesBridge = GimpUtilitiesBridge(
            procedure, Gimp.version()
        )
        logging.debug(self.bridge.base_info)
        sh_client = AiHordeClient(
            VERSION,
            URL_VERSION_UPDATE,
            HELP_URL,
            URL_DOWNLOAD,
            options,
            self.bridge.base_info,
            self.bridge,
        )
        Gimp.progress_init(_("AI Horde work"))
        try:
            images_names = sh_client.generate_image(options)
        except Exception as ex:
            log_exception(ex)
            url_data = self.bridge.get_generated_image_url_status()
            if url_data:
                font = Gimp.Font.get_by_name("Monospace")
                # We try to offer some relief, for the user to still download the image
                if font is None:
                    font = Gimp.fonts_get_list()[0]
                text_layer = Gimp.TextLayer.new(
                    image,
                    url_data[2],
                    font,
                    10,
                    Gimp.Unit.pixel(),
                )
                text_layer.set_name(url_data[0])
                image.insert_layer(text_layer, None, 0)
                Gimp.displays_flush()

                message = (
                    _(
                        "It will take too long, You can continue with your activities while the Horde works."
                    )
                    + "\n  "
                    + url_data[2]
                    + "\n"
                    + str(ex)
                )
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(message),
                )

            elif created_image:
                image.delete()
                Gimp.displays_flush()
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(str(ex)),
            )

        self.display_generated(image, images_names, model)

        self.store_metadata(image, sh_client)

        message = "The task was succesful"

        new_choices = sh_client.settings.get("local_settings", {})
        logging.debug(new_choices)
        self.procedures[procedure_name].update_choices_into(
            new_choices, self.st_manager
        )
        logging.debug("Done")
        message += self.bridge.append_success_message
        message += self.bridge.append_warning
        logging.debug(message)
        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS, GLib.Error(message)
        )

    def store_metadata(self, image: Gimp.Image, sh_client: AiHordeClient) -> None:
        metadata = METADATA_FOR_GIMP.format(
            **{
                "model_name": sh_client.settings["model"],
                "user": getpass.getuser(),
                "prompt": sh_client.settings["prompt"],
                "plugin_name": HORDE_CLIENT_NAME,
                "plugin_version": VERSION,
                "lines_properties": sh_client.get_full_description(),
            }
        )
        logging.debug(metadata)
        new_metadata = Gimp.Metadata().deserialize(metadata)
        logging.debug(new_metadata.serialize())
        image.set_metadata(new_metadata)

    def get_image_data(self, image: Gimp.Image) -> str:
        """
        returns a base encoded representation of the Gimp Image
        """
        if image is None:
            return ""
        Gimp.file_save(
            Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path(init_file), None
        )
        with open(init_file, "rb") as init_image:
            encoded = base64.b64encode(init_image.read()).decode("ascii")
            return encoded
        return ""

    def display_generated(
        self, gimp_image: Gimp.Image, file_names: list[str], name: str
    ):
        """
        Creates a layer in gimp_image for each image from images, sets the name
        of the layer
        """
        color = Gimp.context_get_foreground()
        Gimp.context_set_foreground(Gegl.Color.new("#000000"))

        logging.debug("Creating layers")
        for file_name in file_names:
            new_layer = Gimp.file_load_layer(
                Gimp.RunMode.NONINTERACTIVE,
                gimp_image,
                Gio.File.new_for_path(file_name),
            )
            new_layer.set_name(name)
            gimp_image.insert_layer(new_layer, None, 0)
            os.unlink(file_name)
        Gimp.context_set_foreground(color)
        logging.debug("Layers added")
        Gimp.displays_flush()


class GimpUtilitiesBridge(InformerFrontend):
    """
    Helper to allow AiHordeClient to give back information to the UI
    """

    def __init__(self, procedure: Gimp.ImageProcedure, gimp_version: str):
        super().__init__()

        self.procedure = procedure
        self.base_info = "-_".join(
            [
                HORDE_CLIENT_NAME,
                str(VERSION),
                platform.system(),
                platform.python_version(),
                str(gimp_version),
                platform.machine(),
            ]
        )
        """
        Full name of the AiHorde client
        """

        self.append_warning: str = ""
        self.append_success_message: str = ""

    def set_finished(self):
        Gimp.progress_end()

    def update_status(self, text: str, progress: float = 0.0):
        Gimp.progress_set_text(text)
        Gimp.progress_update(progress / 100.0)

    def show_error(self, message, url="", title="", buttons=0):
        logging.debug(url, title)
        if title == "warning":
            self.append_warning += "\n " + message
            return
        raise Exception(message)

    def show_message(self, message, url="", title="", buttons=0):
        self.append_success_message += "\n " + message
        pass

    def get_frontend_property(self, property_name: str) -> Union[str, bool, None]:
        try:
            info = Gimp.get_parasite(property_name).get_data()[0]
            return info
        except AttributeError:
            return False

    def has_asked_for_update(self) -> bool:
        return self.get_frontend_property(PROPERTY_CURRENT_SESSION)

    def just_asked_for_update(self) -> None:
        self.set_frontend_property(PROPERTY_CURRENT_SESSION, True)

    def set_frontend_property(self, property_name: str, value: Union[str, bool]):
        Gimp.attach_parasite(Gimp.Parasite.new(property_name, 0, [value]))

    def path_store_directory(self) -> str:
        pass


Gimp.main(StableDiffusion.__gtype__, sys.argv)

# TBD
#
# * [X] Add TextLayer telling the URL of the expected
#   image with a time to review the image generation
# * [X] Make sure initial conservative defaults
# * [X] Use metadata to store options
# * [X] NSFW images are not presented, instead error
# * [ ] Use aihordeclient
# * [ ] Add styles for apikey users
# * [ ] Use annotations
# * [ ] Locally make outpaint Extend to left, bottom, right, top:
#      - Enlarge Image with a given amount, max 1.024, transparent
#      - Send to process as inpaint
# * [ ] Upscale image locally: Use Image, Scale Image Interpolation Lohab
#
