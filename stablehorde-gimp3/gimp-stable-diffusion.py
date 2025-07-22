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
import gettext
import json
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


plug_in_proc = "ikks-py3-stablehorde"
plug_in_binary = "py3-stablehorde"

VERSION = 3
DEBUG = False
API_ROOT = "https://stablehorde.net/api/v2/"


HELP_URL = "https://aihorde.net/faq"
REGISTER_URL = "https://aihorde.net/register"
URL_VERSION_UPDATE = "https://raw.githubusercontent.com/ikks/gimp-stable-diffusion/gimp3/stablehorde/version.json"
INIT_FILE = "init.png"
GENERATED_FILE = "stablehorde-generated.png"
ANONYMOUS_KEY = "0000000000"
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

# check every 5 seconds
CHECK_WAIT = 5
MAX_TIME_REFRESH = 15
check_max = None

init_file = r"{}".format(os.path.join(tempfile.gettempdir(), INIT_FILE))
generated_file = r"{}".format(os.path.join(tempfile.gettempdir(), GENERATED_FILE))
scheduler = sched.scheduler(time.time, time.sleep)

check_counter = 0
STATUS_BAR = ["|", "/", "-", "\\"]

# Identifier given by stablehorde
id = None


# Localization helpers
_ = gettext.gettext


def N_(message):
    return message


WORK_MODEL_OPTIONS = [
    ("MODE_TEXT2IMG", N_("Text -> Image"), N_("Generate an image from a description")),
    ("MODE_IMG2IMG", N_("Image -> Image"), N_("Modifiy an image with a description")),
    (
        "MODE_INPAINTING",
        N_("Inpainting"),
        N_("Modify a portion of the image, you need to mark an alpha channel"),
    ),
]

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
    print(f"[{ dnow }] { information }")
    if additional:
        print(additional)


def get_images():
    url = f"{ API_ROOT }generate/status/{ id }"
    with urlopen(url) as response:
        body = response.read()
    data = json.loads(body)
    show_debugging_data(data)

    return data["generations"]


def get_image_data(image, drawable):
    Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path(init_file), None
    )
    with open(init_file, "rb") as init_image:
        encoded = base64.b64encode(init_image.read()).decode("ascii")
        return encoded
    return ""


def check_status():
    url = f"{ API_ROOT }generate/check/{ id }"

    with urlopen(url) as response:
        body = response.read()
    data = json.loads(body)

    show_debugging_data(data)

    global check_counter
    check_counter = check_counter + 1

    if data["processing"] == 0:
        text = (
            "Queue position: "
            + str(data["queue_position"])
            + ", Wait time: "
            + str(data["wait_time"])
            + "s"
        )
    elif data["processing"] > 0:
        text = f"Generating...[{ STATUS_BAR[check_counter%len(STATUS_BAR)] }]"

    show_debugging_data(text + f" {check_counter}")
    Gimp.progress_set_text(text)

    if check_counter < check_max and data["done"] is False:
        if data["is_possible"] is True:
            wait_time = min(max(CHECK_WAIT, data["wait_time"] / 2), MAX_TIME_REFRESH)
            scheduler.enter(wait_time, 1, check_status, ())
            scheduler.run()
        else:
            show_debugging_data(data)
            raise Exception(
                "Currently no worker available to generate your image. Please try again later."
            )
    elif check_counter == check_max:
        minutes = (check_max * CHECK_WAIT) / 60
        show_debugging_data(data)
        raise Exception(
            "Image generation timed out after "
            + str(minutes)
            + " minutes. Please try again later."
        )
    elif data["done"]:
        return


def display_generated(gimp_image, images, model):
    color = Gimp.context_get_foreground()
    Gimp.context_set_foreground(Gegl.Color.new("#000000"))

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
                message = data["message-3"]["en"]
                Gimp.message(message)
            return message
        except (HTTPError, URLError) as ex:
            # No worries if we don't have connection
            ex = ex


def stable_diffussion_run(procedure, run_mode, image, drawables, config, data):
    if len(drawables) > 1:
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Procedure '{plug_in_proc}' works with zero or one layer."),
        )
    elif len(drawables) == 1:
        if not isinstance(drawables[0], Gimp.Layer):
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(f"Procedure '{plug_in_proc}' works with layers only."),
            )

    if run_mode == Gimp.RunMode.INTERACTIVE:
        GimpUi.init(plug_in_binary)

        dialog = GimpUi.ProcedureDialog.new(procedure, config, "Stable Horde")
        dialog.get_widget("prompt-strength", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("nimages", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("init-strength", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("steps", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("max-wait-minutes", GimpUi.SpinScale.__gtype__)
        dialog.set_sensitive_if_in(
            "init-strength",
            None,
            "prompt-type",
            Gimp.ValueArray.new_from_values(["MODE_IMG2IMG"]),
            True,
        )
        dialog.set_sensitive_if_in(
            "nimages",
            None,
            "prompt-type",
            Gimp.ValueArray.new_from_values(["MODE_IMG2IMG", "MODE_INPAINTING"]),
            True,
        )
        dialog.fill(
            [
                "prompt-type",
                "model",
                "prompt-strength",
                "init-strength",
                "steps",
                "nimages",
                "prompt",
                "nsfw",
                "censor-nsfw",
                "api-key",
                "max-wait-minutes",
            ]
        )
        if not dialog.run():
            dialog.destroy()
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
        else:
            dialog.destroy()

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

    global check_max
    check_max = (max_wait_minutes * 60) / CHECK_WAIT

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
            init = get_image_data(image, drawables[0])
            data_to_send.update({"source_image": init})
            data_to_send.update({"source_processing": "img2img"})
            params.update({"denoising_strength": (1 - float(init_strength))})
            params.update({"n": nimages})
        elif mode == "MODE_INPAINTING":
            init = get_image_data(image, drawables[0])
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
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            show_debugging_data(data)

            global id
            id = data["id"]
        except HTTPError as ex:
            try:
                data = ex.read().decode("utf-8")
                data = json.loads(data)
                message = data.get("message", str(ex))
                if data.get("rc", "") == "KudosUpfront":
                    if api_key == ANONYMOUS_KEY:
                        message = _(
                            f"Register at { REGISTER_URL } and use your key to improve your rate success. Detail: { message }"
                        )
                    else:
                        message = _(
                            _(
                                f"{ HELP_URL } to learn to earn kudos. Detail: { message }"
                            )
                        )
            except Exception:
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

        check_status()
        images = get_images()
        display_generated(image, images, model)

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
            GLib.Error(f"Stablehorde said: '{ message }'."),
        )
    except URLError as ex:
        show_debugging_data(str(ex), data)
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Internet required, check your connection: '{ ex }'."),
        )
    except Exception as ex:
        show_debugging_data(str(ex), data)
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Service failed with: '{ ex }'."),
        )
    finally:
        Gimp.progress_end()
        message = check_update()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, message)


class StableDiffussion(Gimp.PlugIn):
    def do_query_procedures(self):
        return [plug_in_proc]

    def do_create_procedure(self, name):
        procedure = None
        if name != plug_in_proc:
            return procedure

        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, stable_diffussion_run, None
        )
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE
            | Gimp.ProcedureSensitivityMask.NO_DRAWABLES
        )
        procedure.set_menu_label("_Stable Horde")
        procedure.set_attribution("ikks", "Igor Tamara", "2025")
        procedure.add_menu_path("<Image>/AI")
        procedure.set_documentation(
            "Generate images with Stable Horde",
            PLUGIN_DESCRIPTION,
            None,
        )

        type_generation_choices = Gimp.Choice.new()
        for i, (name, label, blurb) in enumerate(WORK_MODEL_OPTIONS):
            type_generation_choices.add(name, i, _(label), _(blurb))
        procedure.add_choice_argument(
            "prompt-type",
            _("Do T_his"),
            _("Choose what to do"),
            type_generation_choices,
            WORK_MODEL_OPTIONS[0][0],
            GObject.ParamFlags.READWRITE,
        )

        model_choices = Gimp.Choice.new()
        for i, model_name in enumerate(MODELS):
            model_choices.add(model_name, i, model_name.capitalize(), "")

        procedure.add_choice_argument(
            "model",
            _("_Model to apply"),
            _("Which one"),
            model_choices,
            MODELS[0],
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
            _("More steps means more detailed, affectes time and GPU usage"),
            10,
            150,
            50,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "nimages",
            _("# of _Images"),
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
            _("Seed (optional)"),
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
            _("Get yours at https://stablehorde.net/"),
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
            1,
            GObject.ParamFlags.READWRITE,
        )
        return procedure


Gimp.main(StableDiffussion.__gtype__, sys.argv)

# TBD
# * [ ] Convert to methods and submenus
# * [ ] Use annotations
# * [ ] Localization
# * [ ] Add advanced - Other options exposed in the API
