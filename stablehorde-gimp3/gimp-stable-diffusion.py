#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Gimp3 plugin for StableHorde
# Authors:
#  * blueturtleai <https://github.com/blueturtleai> Original
#  * binarymass <https://github.com/binarymass>
#  * Igor Támara <https://github.com/ikks>
#
#
# MIT lICENSE
# https://github.com/ikks/gimp-stable-diffusion/blob/main/LICENSE

from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime
import base64
import json
import locale
import os
import sched
import sys
import tempfile
import time

import gi

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


VERSION = 5
DEBUG = False

API_ROOT = "https://stablehorde.net/api/v2/"
HELP_URL = "https://aihorde.net/faq"
REGISTER_URL = "https://aihorde.net/register"
URL_VERSION_UPDATE = "https://raw.githubusercontent.com/ikks/gimp-stable-diffusion/gimp3/stablehorde/version.json"
PLUGIN_DESCRIPTION = """Stable Diffussion mixes are powered by https://stablehorde.net/ ,
join, get an API key, earn kudos and create more.  You need Internet to make use
of this plugin.  You can use the power of other GPUs worlwide and help with yours
aswell.  An AI plugin for Gimp that just works.

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
ANONYMOUS_KEY = "0000000000"
# check between 5 and 15 seconds
CHECK_WAIT = 5
MAX_TIME_REFRESH = 15

init_file = r"{}".format(os.path.join(tempfile.gettempdir(), INIT_FILE))
generated_file = r"{}".format(os.path.join(tempfile.gettempdir(), GENERATED_FILE))
scheduler = sched.scheduler(time.time, time.sleep)

STATUS_BAR = ["|", "/", "-", "\\"]


# Localization helpers
def _(message):
    return GLib.dgettext(None, message)


def N_(message):
    return message


MODELS = [
    "AbsoluteReality",
    "AlbedoBase XL (SDXL)",
    "AlbedoBase XL 3.1",
    "AMPonyXL",
    "Analog Madness",
    "Anything Diffusion",
    "Babes",
    "BB95 Furry Mix",
    "BB95 Furry Mix v14",
    "BlenderMix Pony",
    "Counterfeit",
    "CyberRealistic Pony",
    "Deliberate",
    "Deliberate 3.0",
    "Dreamshaper",
    "DreamShaper XL",
    "DucHaiten GameArt (Unreal) Pony",
    "Flux.1-Schnell fp8 (Compact)",
    "Fustercluck",
    "Grapefruit Hentai",
    "Hassaku XL",
    "Hentai Diffusion",
    "HolyMix ILXL",
    "ICBINP - I Can't Believe It's Not Photography",
    "ICBINP XL",
    "Juggernaut XL",
    "KaynegIllustriousXL",
    "majicMIX realistic",
    "NatViS",
    "noobEvo",
    "Nova Anime XL",
    "Nova Furry Pony",
    "NTR MIX IL-Noob XL",
    "Pony Diffusion XL",
    "Pony Realism",
    "Prefect Pony",
    "Realistic Vision",
    "SDXL 1.0",
    "Stable Cascade 1.0",
    "stable_diffusion",
    "SwamPonyXL",
    "TUNIX Pony",
    "Unstable Diffusers XL",
    "WAI-ANI-NSFW-PONYXL",
    "WAI-CUTE Pony",
    "waifu_diffusion",
    "White Pony Diffusion 4",
    "Yiffy",
    "ZavyChromaXL",
]

# This is a list of inpainting models
# For now using only stable_diffusion_inpainting
INPAINT_MODELS = [
    "A-Zovya RPG Inpainting",
    "Anything Diffusion Inpainting",
    "Deliberate Inpainting",
    "DreamShaper Inpainting",
    "Epic Diffusion Inpainting",
    "iCoMix Inpainting",
    "Realistic Vision Inpainting",
    "stable_diffusion_inpainting",
]


def show_debugging_data(information, additional=""):
    if not DEBUG:
        return

    dnow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(information, Exception):
        ln = information.__traceback__.tb_lineno
        print(f"[{ dnow }]{ln}: { information }")
    else:
        print(f"[{ dnow }] { information }")
    if additional:
        print(additional)


def check_update():
    """
    Inform the user regarding a plugin update
    """
    try:
        Gimp.get_parasite("stable_horde_checked_update").get_data()
    except AttributeError as ex:
        try:
            # Check for updates by fetching version information from a URL
            url = URL_VERSION_UPDATE
            response = urlopen(url)
            data = response.read()
            data = json.loads(data)
            ex = ex
            Gimp.attach_parasite(
                Gimp.Parasite.new("stable_horde_checked_update", 1, [1])
            )
            if VERSION < int(data.get("version-3", 1)):
                lang = locale.getlocale()[0][:2]
                message = data["message-3"].get(lang, data["message-3"]["en"])
                Gimp.message(message)
            return message
        except (HTTPError, URLError) as ex:
            # No worries if we don't have connection
            ex = ex


class ProcedureInformation:
    def __init__(
        self, menu_label, model_choices, action, dialog_title, dialog_description
    ):
        self.menu_label = menu_label
        self.model_choices = model_choices
        self.action = action
        self.dialog_title = dialog_title
        self.dialog_description = dialog_description


class StableDiffussion(Gimp.PlugIn):
    plug_in_proc_t2i = "ikks-py3-stablehorde-t2i"
    plug_in_proc_i2i = "ikks-py3-stablehorde-i2i"
    plug_in_proc_inpaint = "ikks-py3-stablehorde-inpaint"
    plug_in_binary = "py3-stablehorde"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.t2i = ProcedureInformation(
            # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
            menu_label=_("_Create Image from Prompt"),
            model_choices=MODELS,
            action="MODE_TEXT2IMG",
            # TRANSLATORS: Dialog title
            dialog_title=_("From Text"),
            dialog_description=_("Create an image from a prompt"),
        )
        self.i2i = ProcedureInformation(
            # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
            menu_label=_("_Transform Image with Prompt"),
            model_choices=MODELS,
            action="MODE_IMG2IMG",
            # TRANSLATORS: Dialog title
            dialog_title=_("Transform"),
            dialog_description=_("Transform a source image with a prompt"),
        )
        self.in_paint = ProcedureInformation(
            # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
            menu_label=_("Adjust Image _Region"),
            model_choices=INPAINT_MODELS,
            action="MODE_INPAINTING",
            # TRANSLATORS: Dialog title
            dialog_title=_("Inpaint"),
            dialog_description=_("Replace a portion of the image"),
        )

        self.procedures = {
            self.plug_in_proc_t2i: self.t2i,
            self.plug_in_proc_i2i: self.i2i,
            self.plug_in_proc_inpaint: self.in_paint,
        }

        self.plug_in_procs = list(self.procedures.keys())

    def do_query_procedures(self):
        return self.plug_in_procs

    def do_create_procedure(self, name):
        procedure = None
        self.check_counter = 0
        self.check_max = None
        if name not in self.plug_in_procs:
            return procedure

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
        procedure.add_menu_path("<Image>/AI/Stable _Horde")
        procedure.set_documentation(
            self.procedures[name].dialog_description,
            PLUGIN_DESCRIPTION,
            None,
        )
        procedure.add_int_argument(
            "width",
            _("W_idth"),
            None,
            384,
            1024,
            512,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "height",
            _("Height"),
            None,
            384,
            1024,
            384,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_string_argument(
            "prompt-type",
            "Action to execute",
            "Choose what to do",
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
            _("Which one"),
            model_choices,
            initial_selection,
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_double_argument(
            "init-strength",
            _("Init Stren_gth"),
            _(
                "The higher the value, your initial image will have more relevance when transforming"
            ),
            0.0,
            1.0,
            0.3,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_double_argument(
            "prompt-strength",
            _("Prompt Stre_ngth"),
            _("How much the AI will follow the prompt, the higher, the more obedient"),
            0,
            20,
            8,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "steps",
            _("S_teps"),
            _("More steps mean more details, affects time and GPU usage"),
            10,
            150,
            50,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "nimages",
            _("_# of Images"),
            _(
                "Number of images to view the transformation from the original to the target prompt"
            ),
            1,
            10,
            1,
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_string_argument(
            "seed",
            _("S_eed (optional)"),
            _(
                "If you want the process repeatable, put something here, otherwise, enthropy will win"
            ),
            "",
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_string_argument(
            "prompt",
            _("_Prompt"),
            _(
                "Let your imagination run wild or put a proper description of your desired output."
            ),
            "Draw a beautiful...",
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "nsfw",
            _("NSF_W"),
            _("If not marked, it's faster, when marked you are on the edge..."),
            False,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "censor-nsfw",
            _("Censor NS_FW"),
            _("Allow if you want to avoid unexpected images..."),
            False,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_string_argument(
            "api-key",
            _("API _key (optional)"),
            _("Get yours at https://stablehorde.net/ for free"),
            "",
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "max-wait-minutes",
            _("Max Wait (min_utes)"),
            _(
                "Depends on your patience and your kudos.  You'll get a complain message if timeout is reached"
            ),
            1,
            5,
            3,
            GObject.ParamFlags.READWRITE,
        )
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        procedure_name = procedure.get_name()
        if image is None and procedure_name in [
            self.plug_in_proc_i2i,
            self.plug_in_proc_inpaint,
        ]:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(f"Procedure '{procedure_name}' requires an image."),
            )
        if len(drawables) > 1:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(
                    f"Procedure '{procedure.name}' works with zero or one layer."
                ),
            )
        elif len(drawables) == 1:
            if not isinstance(drawables[0], Gimp.Layer):
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(f"Procedure '{procedure.name}' works with layers only."),
                )

        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init(self.plug_in_binary)

            dialog = GimpUi.ProcedureDialog.new(
                procedure,
                config,
                f"Stable Horde - { self.procedures[procedure_name].dialog_title }",
            )
            dialog.get_widget("prompt-strength", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("nimages", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("init-strength", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("steps", GimpUi.SpinScale.__gtype__)
            dialog.get_widget("max-wait-minutes", GimpUi.SpinScale.__gtype__)

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
                    "api-key",
                    "max-wait-minutes",
                ]
            )
            dialog.fill(controls_to_show)
            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
            else:
                dialog.destroy()

        if image is None and procedure_name == self.plug_in_proc_t2i:
            width = config.get_property("width")
            height = config.get_property("height")
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
            drawables = [layer]
            Gimp.Display.new(image)

        model = config.get_property("model")
        mode = config.get_property("prompt-type")
        init_strength = config.get_property("init-strength")
        prompt_strength = config.get_property("prompt-strength")
        steps = config.get_property("steps")
        prompt = config.get_property("prompt")
        nsfw = config.get_property("nsfw")
        censor_nsfw = config.get_property("censor-nsfw")
        api_key = config.get_property("api-key") or ANONYMOUS_KEY
        max_wait_minutes = config.get_property("max-wait-minutes")
        seed = config.get_property("seed")
        nimages = config.get_property("nimages")
        show_debugging_data(api_key)
        image_width = image.get_width()
        image_height = image.get_height()
        if (
            image_width < 384
            or image_width > 1024
            or image_height < 384
            or image_height > 1024
        ):
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_("Your image needs to be between 384x384 and 1024x1024.")),
            )

        if prompt == "":
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_("Please enter a prompt.")),
            )

        if mode == "MODE_INPAINTING" and drawables[0].has_alpha == 0:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_("When inpainting, the image must have an alpha channel.")),
            )

        Gimp.progress_init(_("Starting Horde work..."))

        self.check_max = (max_wait_minutes * 60) / CHECK_WAIT
        self.id = ""

        try:
            params = {
                "cfg_scale": float(prompt_strength),
                "steps": int(steps),
                "seed": seed,
            }

            data_to_send = {
                "params": params,
                "prompt": prompt,
                "nsfw": nsfw,
                "censor_nsfw": censor_nsfw,
                "r2": True,
            }

            if image_width % 64 != 0:
                width = int(image_width / 64) * 64
            else:
                width = image_width

            if image_height % 64 != 0:
                height = int(image_height / 64) * 64
            else:
                height = image_height

            params.update({"width": int(width)})
            params.update({"height": int(height)})

            data_to_send.update({"models": [model]})
            if mode == "MODE_IMG2IMG":
                init = self.get_image_data(image, drawables[0])
                data_to_send.update({"source_image": init})
                data_to_send.update({"source_processing": "img2img"})
                params.update({"denoising_strength": (1 - float(init_strength))})
                params.update({"n": nimages})
            elif mode == "MODE_INPAINTING":
                init = self.get_image_data(image, drawables[0])
                model = "stable_diffusion_inpainting"
                data_to_send.update({"models": [model]})
                data_to_send.update({"source_image": init})
                data_to_send.update({"source_processing": "inpainting"})
                params.update({"n": nimages})

            data_to_send = json.dumps(data_to_send)
            post_data = data_to_send.encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "apikey": api_key,
            }
            url = f"{ API_ROOT }generate/async"

            request = Request(url, headers=headers, data=post_data)
            try:
                show_debugging_data(data_to_send)
                with urlopen(request, timeout=15) as response:
                    data = json.loads(response.read().decode("utf-8"))
                show_debugging_data(data)

                self.id = data["id"]
            except HTTPError as ex:
                try:
                    data = ex.read().decode("utf-8")
                    data = json.loads(data)
                    message = data.get("message", str(ex))
                    if data.get("rc", "") == "KudosUpfront":
                        if api_key == ANONYMOUS_KEY:
                            message = (
                                _(
                                    f"Register at { REGISTER_URL } and use your key to improve your rate success. Detail:"
                                )
                                + f" { message }"
                            )
                        else:
                            message = (
                                f"{ HELP_URL } "
                                + _("to learn to earn kudos. Detail:")
                                + " { message }"
                            )
                except Exception as ex2:
                    show_debugging_data(ex2, "No way to recover error msg")
                    message = str(ex)
                show_debugging_data(message, data)
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(f"'{ message }'."),
                )
            except URLError as ex:
                show_debugging_data(str(ex), data)
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(
                        _("Internet required, chek your connection: ") + f"'{ ex }'."
                    ),
                )
            except Exception as ex:
                show_debugging_data(str(ex), data)
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CALLING_ERROR,
                    GLib.Error(f"{ ex }"),
                )

            self.check_status()
            images = self.get_images()
            self.display_generated(image, images, model)

        except HTTPError as ex:
            try:
                data = ex.read().decode("utf-8")
                data = json.loads(data)
                message = data.get("message", str(ex))
            except Exception:
                message = str(ex)
            show_debugging_data(message, data)
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_(f"Stablehorde said: '{ message }'.")),
            )
        except URLError as ex:
            show_debugging_data(str(ex), data)
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_(f"Internet required, check your connection: '{ ex }'.")),
            )
        except Exception as ex:
            show_debugging_data(str(ex), data)
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_(f"Service failed with: '{ ex }'.")),
            )
        finally:
            Gimp.progress_end()
            message = check_update()

        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS, GLib.Error(message)
        )

    def check_status(self):
        url = f"{ API_ROOT }generate/check/{ self.id }"

        with urlopen(url) as response:
            body = response.read()
        data = json.loads(body)

        show_debugging_data(data)

        self.check_counter = self.check_counter + 1

        if data["processing"] == 0:
            text = (
                _("Queue position: ")
                + str(data["queue_position"])
                + _(", Wait time: ")
                + str(data["wait_time"])
                + _("s")
            )
        elif data["processing"] > 0:
            text = f"Generating...[{ STATUS_BAR[self.check_counter%len(STATUS_BAR)] }]"

        show_debugging_data(text + f" {self.check_counter}")
        Gimp.progress_set_text(text)

        if self.check_counter < self.check_max and data["done"] is False:
            if data["is_possible"] is True:
                wait_time = min(
                    max(CHECK_WAIT, data["wait_time"] / 2), MAX_TIME_REFRESH
                )
                scheduler.enter(wait_time, 1, self.check_status, ())
                scheduler.run()
            else:
                show_debugging_data(data)
                raise Exception(
                    _(
                        "Currently no worker available to generate your image. Please try again later."
                    )
                )
        elif self.check_counter >= self.check_max:
            minutes = (self.check_max * CHECK_WAIT) / 60
            show_debugging_data(data)
            raise Exception(
                _(f"Image generation timed out after { minutes } minutes.")
                + _("Please try again later.")
            )
        elif data["done"]:
            return

    def get_images(self):
        url = f"{ API_ROOT }generate/status/{ self.id }"
        with urlopen(url) as response:
            body = response.read()
        data = json.loads(body)
        show_debugging_data(data)

        return data["generations"]

    def get_image_data(self, image, drawable):
        Gimp.file_save(
            Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path(init_file), None
        )
        with open(init_file, "rb") as init_image:
            encoded = base64.b64encode(init_image.read()).decode("ascii")
            return encoded
        return ""

    def display_generated(self, gimp_image, images, model):
        color = Gimp.context_get_foreground()
        Gimp.context_set_foreground(Gegl.Color.new("#000000"))

        show_debugging_data("Start to download generated images")
        for image in images:
            if image["img"].startswith("https"):
                with urlopen(image["img"]) as response:
                    bytes = response.read()
            else:
                bytes = base64.b64decode(image["img"])

            show_debugging_data(f"dumping to { generated_file }")

            with open(generated_file, "wb+") as image_file:
                image_file.write(bytes)
            new_layer = Gimp.file_load_layer(
                Gimp.RunMode.NONINTERACTIVE,
                gimp_image,
                Gio.File.new_for_path(generated_file),
            )
            new_layer.set_name(model)
            gimp_image.insert_layer(new_layer, None, 0)
        Gimp.context_set_foreground(color)
        return


Gimp.main(StableDiffussion.__gtype__, sys.argv)

# TBD
# * [ ] Improve the ticking in the bar
# * [ ] Use annotations
# * [ ] Localization
# cd po && xgettext -o gimp-stable-diffusion.pot --add-comments=TRANSLATORS: --keyword=_ --flag=_:1:pass-python-format --directory=.. gimp-stable-diffusion.py && cd ..
