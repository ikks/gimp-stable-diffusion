#!/usr/bin/python3
# -*- coding: utf-8 -*-

from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
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


_ = gettext.gettext

plug_in_proc = "ikks-py3-stablehorde"
plug_in_binary = "py3-stablehorde"

VERSION = 1
INIT_FILE = "init.png"
GENERATED_FILE = "stablehorde-generated.png"
API_ROOT = "https://stablehorde.net/api/v2/"

# check every 5 seconds
CHECK_WAIT = 5
check_max = None

init_file = r"{}".format(os.path.join(tempfile.gettempdir(), INIT_FILE))
generated_file = r"{}".format(os.path.join(tempfile.gettempdir(), GENERATED_FILE))
scheduler = sched.scheduler(time.time, time.sleep)

check_counter = 0

# Identifier given by stablehorde
id = None


# Localization helper
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


def get_images():
    url = f"{ API_ROOT }generate/status/{ id }"
    with urlopen(url) as response:
        body = response.read()
    data = json.loads(body)

    print(data)

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
        text = "Generating..."

    print(text + f" {check_counter}")
    Gimp.progress_set_text(text)

    if check_counter < check_max and data["done"] is False:
        if data["is_possible"] is True:
            scheduler.enter(CHECK_WAIT, 1, check_status, ())
            scheduler.run()
        else:
            raise Exception(
                "Currently no worker available to generate your image. Please try again later."
            )
    elif check_counter == check_max:
        minutes = (check_max * CHECK_WAIT) / 60
        raise Exception(
            "Image generation timed out after "
            + str(minutes)
            + " minutes. Please try again later."
        )
    elif data["done"]:
        return


def display_generated(gimp_image, images):
    color = Gimp.context_get_foreground()
    Gimp.context_set_foreground(Gegl.Color.new("#000000"))

    for image in images:
        if image["img"].startswith("https"):
            with urlopen(image["img"]) as response:
                bytes = response.read()
        else:
            bytes = base64.b64decode(image["img"])

        print(f"dumping to { generated_file }")

        with open(generated_file, "wb+") as image_file:
            image_file.write(bytes)
        new_layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE,
            gimp_image,
            Gio.File.new_for_path(generated_file),
        )
        gimp_image.insert_layer(new_layer, None, 0)
    Gimp.context_set_foreground(color)
    return


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
        dialog.get_widget("init-strength", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("prompt-strength", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("steps", GimpUi.SpinScale.__gtype__)
        dialog.get_widget("max-wait-minutes", GimpUi.SpinScale.__gtype__)
        dialog.fill(
            [
                "prompt-type",
                "init-strength",
                "prompt-strength",
                "steps",
                "prompt",
                "nsfw",
                "api-key",
                "max-wait-minutes",
            ]
        )
        if not dialog.run():
            dialog.destroy()
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
        else:
            dialog.destroy()

    mode = config.get_property("prompt-type")
    init_strength = config.get_property("init-strength")
    prompt_strength = config.get_property("prompt-strength")
    steps = config.get_property("steps")
    prompt = config.get_property("prompt")
    nsfw = config.get_property("nsfw")
    api_key = config.get_property("api-key") or "0000000000"
    max_wait_minutes = config.get_property("max-wait-minutes")
    seed = config.get_property("seed")

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

    Gimp.progress_init(_("Generating..."))

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
            "censor_nsfw": False,
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

        if mode == "MODE_IMG2IMG":
            init = get_image_data(image, drawables[0])
            data_to_send.update({"source_image": init})
            data_to_send.update({"source_processing": "img2img"})
            params.update({"denoising_strength": (1 - float(init_strength))})
        elif mode == "MODE_INPAINTING":
            init = get_image_data(image, drawables[0])
            models = ["stable_diffusion_inpainting"]
            data_to_send.update({"source_image": init})
            data_to_send.update({"source_processing": "inpainting"})
            data_to_send.update({"models": models})

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
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            print(data)

            global id
            id = data["id"]
        except URLError as ex:
            print(str(ex))
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(
                    _("Internet required, chek your connection: ") + f"'{ ex }'."
                ),
            )
        except Exception as ex:
            print(str(ex))
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(f"{ ex }"),
            )

        check_status()
        images = get_images()
        display_generated(image, images)

    except HTTPError as ex:
        try:
            data = ex.read()
            data = json.loads(data)

            if "message" in data:
                message = data["message"]
            else:
                message = str(ex)
        except Exception:
            message = str(ex)

        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Stablehorde said: '{ message }'."),
        )
    except URLError as ex:
        print(str(ex))
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Internet required, chek your connection: '{ ex }'."),
        )
    except Exception as ex:
        print(str(ex))
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Service failed with: '{ ex }'."),
        )
    finally:
        Gimp.progress_end()
        # check_update()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


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
            "Join on https://stablehorde.net/ "
            + "earn kudos and get your own API key.",
            None,
        )

        type_generation_choices = Gimp.Choice.new()
        for i, (name, label, blurb) in enumerate(WORK_MODEL_OPTIONS):
            type_generation_choices.add(name, i, _(label), _(blurb))
        procedure.add_choice_argument(
            "prompt-type",
            _("Do _This"),
            _("Choose what to do"),
            type_generation_choices,
            WORK_MODEL_OPTIONS[0][0],
            GObject.ParamFlags.READWRITE,
        )

        procedure.add_double_argument(
            "init-strength",
            "Init Str_ength",
            "The higher the value, your initial image will have more importance",
            0.0,
            1.0,
            0.3,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_double_argument(
            "prompt-strength",
            "Prompt Str_ength",
            "How much the AI will follow the prompt, the higher, the more obedient",
            0,
            20,
            8,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "steps",
            "_Steps",
            "More steps means more detailed, affectes time and GPU usage",
            10,
            150,
            50,
            GObject.ParamFlags.READWRITE,
        )
        (
            procedure.add_string_argument(
                "seed",
                "Seed (optional)",
                "If you want the process repeatable, put something here, otherwise, enthropy will win",
                "",
                GObject.ParamFlags.READWRITE,
            ),
        )
        procedure.add_string_argument(
            "prompt",
            "_Prompt",
            "Let your imagination run wild or put a proper description of your desired output.",
            "Draw a beautiful...",
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_boolean_argument(
            "nsfw",
            "NSF_W",
            "If not marked, it's faster...",
            False,
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_string_argument(
            "api-key",
            "API _key (optional)",
            "Get yours at https://stablehorde.net/",
            "",
            GObject.ParamFlags.READWRITE,
        )
        procedure.add_int_argument(
            "max-wait-minutes",
            "Max Wait (_minutes)",
            "Depends on your patience and your kudos.  You'll get a complain message if timeout is reached",
            1,
            5,
            1,
            GObject.ParamFlags.READWRITE,
        )
        return procedure


Gimp.main(StableDiffussion.__gtype__, sys.argv)

# TBD
# * [ ] Add Model
# * [ ] Add generations
# * [ ] Add v3 check_update
# * [ ] Use annotations
# * [ ] Localization
# * [ ] Add advanced - Other options exposed in the API
