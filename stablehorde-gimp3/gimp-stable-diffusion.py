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


import abc
import asyncio
import base64
import gi
import json
import locale
import logging
import platform
import os
import sys
import tempfile
import time
import traceback

from datetime import date
from datetime import datetime
from pathlib import Path
from time import sleep
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

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


VERSION = "3.0"
DEBUG = False

log_file = os.path.join(tempfile.gettempdir(), "gimp-stable-diffusion.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

HELP_URL = "https://aihorde.net/faq"
"""
Help url for the extension
"""

URL_VERSION_UPDATE = "https://raw.githubusercontent.com/ikks/gimp-stable-diffusion/main/stablehorde/version.json"
"""
Latest version for the extension
"""

PROPERTY_CURRENT_SESSION = "py3-stablehorde-checked-update"

URL_DOWNLOAD = (
    "https://github.com/ikks/libreoffice-stable-diffusion/blob/main/loshd.oxt"
)
"""
Download URL for libreoffice-stable-diffusion
"""

HORDE_CLIENT_NAME = "StableHordeForGimp"
"""
Name of the client sent to API
"""

API_ROOT = "https://stablehorde.net/api/v2/"
REGISTER_STABLE_HORDE_URL = "https://aihorde.net/register"
REGISTER_URL = "https://aihorde.net/register"

PLUGIN_DESCRIPTION = """Stable Diffusion mixes are powered by https://stablehorde.net/ ,
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
ANONYMOUS_KEY = "0000000000"
# check between 5 and 15 seconds
CHECK_WAIT = 5
MAX_TIME_REFRESH = 15

init_file = r"{}".format(os.path.join(tempfile.gettempdir(), INIT_FILE))
generated_file = r"{}".format(os.path.join(tempfile.gettempdir(), GENERATED_FILE))

STATUS_BAR = ["|", "/", "-", "\\"]


# Localization helpers
def _(message):
    return GLib.dgettext(None, message)


def show_debugging_data(information, additional=""):
    if not DEBUG:
        return

    dnow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(information, Exception):
        ln = information.__traceback__.tb_lineno
        logging.error(f"[{ dnow }]{ln}: { information }")
        logging.error(
            "".join(
                traceback.format_exception(None, information, information.__traceback__)
            )
        )
    else:
        logging.debug(f"[{ dnow }] { information }")
    if additional:
        logging.debug(f"[{ dnow }]{additional}")


ANONYMOUS = "0000000000"
"""
api_key for anonymous users
"""

DEFAULT_MODEL = "stable_diffusion"
"""
Model that is always present for image generation
"""

MIN_WIDTH = 384
MAX_WIDTH = 1024
MIN_HEIGHT = 384
MAX_HEIGHT = 1024
MIN_PROMPT_LENGTH = 10
"""
It's  needed that the user writes down something to create an image from
"""

MODELS = [
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
]
"""
Initial list of models, new ones are downloaded from StableHorde API
"""

INPAINT_MODELS = [
    "A-Zovya RPG Inpainting",
    "Anything Diffusion Inpainting",
    "Epic Diffusion Inpainting",
    "iCoMix Inpainting",
    "Realistic Vision Inpainting",
    "stable_diffusion_inpainting",
]
"""
Initial list of inpainting models, new ones are downloaded from StableHorde API
"""


class IdentifiedError(Exception):
    """
    Exception raised for identified problems

    Attributes:
        message -- explanation of the error
        url -- Resource to understand and fix the problem
    """

    def __init__(self, message: str = "A custom error occurred", url: str = ""):
        self.message: str = message
        self.url: str = url
        super().__init__(self.message)

    def __str__(self):
        return self.message


class InformerFrontendInterface(metaclass=abc.ABCMeta):
    """
    Implementing this interface for an application frontend
    gives StableHordeClient a way to inform progress.  It's
    expected that StableHordeClient receives as parameter
    an instance of this Interface to be able to send messages
    and updates to the user.
    """

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "show_message")
            and callable(subclass.show_message)
            and hasattr(subclass, "show_error")
            and callable(subclass.show_error)
            and hasattr(subclass, "get_frontend_property")
            and callable(subclass.get_frontend_property)
            and hasattr(subclass, "set_frontend_property")
            and callable(subclass.set_frontend_property)
            and hasattr(subclass, "update_status")
            and callable(subclass.set_frontend_property)
            and hasattr(subclass, "set_finished")
            and callable(subclass.set_finished)
            and hasattr(subclass, "path_store_directory")
            and callable(subclass.path_store_directory)
            or NotImplemented
        )

    @abc.abstractclassmethod
    def show_message(
        self, message: str, url: str = "", title: str = "", buttons: int = 0
    ):
        """
        Shows an informative message dialog
        if url is given, shows OK, Cancel, when the user presses OK, opens the URL in the
        browser
        title is the title of the dialog to be shown
        buttons are the options that the user can have
        """
        raise NotImplementedError

    @abc.abstractclassmethod
    def show_error(self, message, url="", title="", buttons=0):
        """
        Shows an error message dialog
        if url is given, shows OK, Cancel, when the user presses OK, opens the URL in the
        browser
        title is the title of the dialog to be shown
        buttons are the options that the user can have
        """
        raise NotImplementedError

    @abc.abstractclassmethod
    def get_frontend_property(self, property_name: str) -> str | bool | None:
        """
        Gets a property from the frontend application, used to retrieved stored
        information during this session.  Used when checking for update.
        """
        raise NotImplementedError

    @abc.abstractclassmethod
    def set_frontend_property(self, property_name: str, value: str | bool):
        """
        Sets a property in the frontend application, used to retrieved stored
        information during this session.  Used when checking for update.
        """
        raise NotImplementedError

    @abc.abstractclassmethod
    def update_status(self, text: str, progress: float = 0.0):
        """
        Updates the status to the frontend and the progress from 0 to 100
        """
        raise NotImplementedError

    @abc.abstractclassmethod
    def set_finished(self):
        """
        Tells the frontend that the process has finished successfully
        """
        raise NotImplementedError

    @abc.abstractclassmethod
    def path_store_directory(self) -> str:
        """
        Returns the basepath for the directory offered by the frontend
        to store data for the plugin, cache and user settings
        """
        raise NotImplementedError


class StableHordeClient:
    """
    Interaction with Stable Horde platform, currently supports:
    * Fetch the most used models in the month
    * Review the credits of an api_key
    * Request an image async and go all the way down until getting the image
    * Check if there is a newer version of the frontend client

    Attributes:
        settings -- configured in the constructor and later updated
    """

    # check model updates
    MAX_DAYS_MODEL_UPDATE = 5
    """
    We check at least this number of days for new models
    """

    MAX_MODELS_LIST = 50
    """
    Max Number of models to be presented to the user
    """

    CHECK_WAIT = 5
    """
    Number of seconds to wait before checking again if the image is generated
    """

    MAX_TIME_REFRESH = 15
    """
    If we are in a queue waiting, this is the max time in seconds before asking
    if we are still in queue
    """

    def __init__(
        self,
        settings: json = None,
        platform: str = HORDE_CLIENT_NAME,
        informer: InformerFrontendInterface = None,
    ):
        """
        Creates a Stable Horde client with the settings, if None, the API_KEY is
        set to ANONYMOUS, the name to identify the client to Stable Horde and
        a reference of an obect that allows the client to send messages to the
        user.
        """
        if settings is None:
            self.settings = {"api_key": ANONYMOUS}
        else:
            self.settings: json = settings

        self.api_key: str = self.settings["api_key"]
        self.client_name: str = platform
        self.headers: json = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "apikey": self.api_key,
            "Client-Agent": self.client_name,
        }
        self.informer: InformerFrontendInterface = informer
        self.progress: float = 0.0
        self.progress_text: str = _("Starting")
        self.warnings: list[json] = []

        # Sync informer and async request
        self.finished_task: bool = True
        dt = self.headers.copy()
        del dt["apikey"]
        # Beware, not logging the api_key
        show_debugging_data(dt)

    def __url_open__(
        self, url: str | Request, timeout: float = 10, refresh_each: float = 0.5
    ) -> None:
        """
        Opens a url request async with standard urllib, taking into account
        timeout informs `refresh_each` seconds.

        Requires Python 3.9

        Uses self.finished_task
        Invokes self.__inform_progress__()
        Stores the result in self.response_data
        """

        def real_url_open():
            show_debugging_data(f"starting request {url}")
            with urlopen(url, timeout=timeout) as response:
                show_debugging_data("Data arrived")
                self.response_data = json.loads(response.read().decode("utf-8"))
            self.finished_task = True

        async def counter(until: int = 10) -> None:
            now = time.perf_counter()
            initial = now
            for i in range(0, until):
                if self.finished_task:
                    show_debugging_data(f"Request took {now - initial}")
                    break
                await asyncio.sleep(refresh_each)
                now = time.perf_counter()
                self.__inform_progress__()

        async def requester_with_counter() -> None:
            the_counter = asyncio.create_task(counter(int(timeout / refresh_each)))
            await asyncio.to_thread(real_url_open)
            await the_counter
            show_debugging_data("finished request")

        self.finished_task = False
        asyncio.run(requester_with_counter())

    def refresh_models(self):
        """
        Refreshes the model list with the 50 more used including always stable_diffusion
        we update self.settings to store the date when the models were stored.
        """
        previous_update = self.settings.get(
            "local_settings", {"date_refreshed_models": "2025-07-01"}
        ).get("date_refreshed_models", "2025-07-01")
        today = datetime.now().date()
        days_updated = (
            today - date(*[int(i) for i in previous_update.split("-")])
        ).days
        if days_updated < StableHordeClient.MAX_DAYS_MODEL_UPDATE:
            show_debugging_data(f"No need to update models {previous_update}")
            return

        show_debugging_data("time to update models")
        locals = self.settings.get("local_settings", {"models": MODELS})
        locals["date_refreshed_models"] = today.strftime("%Y-%m-%d")

        url = API_ROOT + "/stats/img/models?model_state=known"
        self.headers["X-Fields"] = "month"

        self.progress_text = _("Updating models")
        self.__inform_progress__()
        try:
            self.__url_open__(url)
            del self.headers["X-Fields"]
        except (HTTPError, URLError):
            message = _(
                "Tried to get the latest models, check your Internet connection"
            )
            self.informer.show_error(message)
            return
        except TimeoutError:
            show_debugging_data("Failed updating models due to timeout")
            return

        # Select the most popular models
        popular_models = sorted(
            [(key, val) for key, val in self.response_data["month"].items()],
            key=lambda c: c[1],
            reverse=True,
        )
        show_debugging_data(f"Downloaded {len(popular_models)}")
        if self.settings.get("mode", "") == "MODE_INPAINTING":
            popular_models = [
                (key, val)
                for key, val in popular_models
                if key.lower().count("inpaint") > 0
            ][: StableHordeClient.MAX_MODELS_LIST]
        else:
            popular_models = [
                (key, val)
                for key, val in popular_models
                if key.lower().count("inpaint") == 0
            ][: StableHordeClient.MAX_MODELS_LIST]

        fetched_models = [model[0] for model in popular_models]
        default_model = self.settings.get("default_model", DEFAULT_MODEL)
        if default_model not in fetched_models:
            fetched_models.append(default_model)
        if len(fetched_models) > 3:
            compare = set(fetched_models)
            new_models = compare.difference(locals["models"])
            if new_models:
                show_debugging_data(f"New models {len(new_models)}")
                locals["models"] = sorted(fetched_models, key=lambda c: c.upper())
                if len(new_models) == 1:
                    message = _("We have a new model:\n\n * ") + new_models[0]
                else:
                    message = _("We have new models:\n * ") + "\n * ".join(new_models)

                self.informer.show_message(message)

        self.settings["local_settings"] = locals

        if self.settings["model"] not in locals["models"]:
            self.settings["model"] = locals["models"][0]
        show_debugging_data(self.settings["local_settings"])

    def refresh_styles(self):
        """
        Refreshes the style list
        """
        # Fetch first 50 more used styles
        # We store the name of the styles and the date the last request was done
        # We fetch the style list if it haven't been updated during 5 days
        pass

    def check_update(self) -> str:
        """
        Inform the user regarding a plugin update. Returns "" if the
        installed is the latest one. Else the localized message,
        defaulting to english if there is no locale for the message.

        Uses PROPERTY_CURRENT_SESSION as the name of the property for
        checking only during this session.
        """
        current_local_session_key = PROPERTY_CURRENT_SESSION
        already_asked = self.informer.get_frontend_property(current_local_session_key)

        if already_asked:
            show_debugging_data(
                "We already checked for a new version during this session"
            )
            return ""
        show_debugging_data("Checking for update")

        try:
            # Check for updates by fetching version information from a URL
            url = URL_VERSION_UPDATE
            self.__url_open__(url, 15)
            data = self.response_data

            # During this session we will not check for update
            self.informer.set_frontend_property(current_local_session_key, True)
            local_version = (*(int(i) for i in str(VERSION).split(".")),)
            if isinstance(data["version"], int):
                # incoming_version has a deprecated format, local is newer
                return ""
            incoming_version = (*(int(i) for i in data["version"].split(".")),)

            if local_version < incoming_version:
                lang = locale.getlocale()[0][:2]
                message = data["message"].get(lang, data["message"]["en"])
            message = data["message"].get(lang, data["message"]["en"])
        except (HTTPError, URLError):
            message = _(
                "Tried to check for most recent version, check your Internet connection"
            )
        return message

    def get_balance(self) -> str:
        """
        Given an Stable Horde token, present in the attribute api_key,
        returns the balance for the account. If happens to be an
        anonymous account, invites to register
        """
        if self.api_key == ANONYMOUS:
            return _("Register at ") + REGISTER_STABLE_HORDE_URL
        url = API_ROOT + "find_user"
        request = Request(url, headers=self.headers)
        try:
            self.__url_open__(request, 15)
            data = self.response_data
            show_debugging_data(data)
        except HTTPError as ex:
            raise (ex)

        return f"\n\nYou have { data['kudos'] } kudos"

    def generate_image(self, options: json) -> [str]:
        """
        options have been prefilled for the selected model
        informer will be acknowledged on the process via show_progress
        Executes the flow to get an image from Stable Horde

        1. Invokes endpoint to launch a work for image generation
        2. Reviews the status of the work
        3. Waits until the max_wait_minutes for the generation of
        the image
        4. Retrieves the resulting images and returns the local path of
        the downloaded images

        When no success, returns [].  raises exceptions, but tries to
        offer helpful messages
        """
        self.settings.update(options)
        self.api_key = options["api_key"]
        self.headers["apikey"] = self.api_key
        self.check_counter = 1
        self.check_max = (
            options["max_wait_minutes"] * 60
        ) / StableHordeClient.CHECK_WAIT
        # Id assigned when requesting the generation of an image
        self.id = ""

        # Used for the progressbar.  We depend on the max time the user indicated
        self.max_time = datetime.now().timestamp() + options["max_wait_minutes"] * 60
        self.factor = 5 / (
            3.0 * options["max_wait_minutes"]
        )  # Percentage and minutes 100*ellapsed/(max_wait*60)

        self.progress_text = _("Contacting the Horde")
        try:
            params = {
                "cfg_scale": float(options["prompt_strength"]),
                "steps": int(options["steps"]),
                "seed": options["seed"],
            }

            data_to_send = {
                "params": params,
                "prompt": options["prompt"],
                "nsfw": options["nsfw"],
                "censor_nsfw": options["censor_nsfw"],
                "r2": True,
            }

            if options["image_width"] % 64 != 0:
                width = int(options["image_width"] / 64) * 64
            else:
                width = options["image_width"]

            if options["image_height"] % 64 != 0:
                height = int(options["image_height"] / 64) * 64
            else:
                height = options["image_height"]

            params.update({"width": int(width)})
            params.update({"height": int(height)})

            data_to_send.update({"models": [options["model"]]})

            mode = options.get("mode", "")
            if mode == "MODE_IMG2IMG":
                data_to_send.update({"source_image": options["source_image"]})
                data_to_send.update({"source_processing": "img2img"})
                params.update(
                    {"denoising_strength": (1 - float(options["init_strength"]))}
                )
                params.update({"n": options["nimages"]})
            elif mode == "MODE_INPAINTING":
                data_to_send.update({"source_image": options["source_image"]})
                data_to_send.update({"source_processing": "inpainting"})
                params.update({"n": options["nimages"]})

            dt = data_to_send.copy()
            if "source_image" in dt:
                del dt["source_image"]
                dt["source_image_size"] = len(data_to_send["source_image"])
            show_debugging_data(dt)

            data_to_send = json.dumps(data_to_send)

            post_data = data_to_send.encode("utf-8")

            url = f"{ API_ROOT }generate/async"

            request = Request(url, headers=self.headers, data=post_data)
            try:
                self.__inform_progress__()
                self.__url_open__(request, 15)
                data = self.response_data
                show_debugging_data(data)
                if "warnings" in data:
                    self.warnings = data["warnings"]
                text = _("Horde Contacted")
                show_debugging_data(text + f" {self.check_counter} { self.progress }")
                self.progress_text = text
                self.__inform_progress__()
                self.id = data["id"]
            except HTTPError as ex:
                try:
                    data = ex.read().decode("utf-8")
                    data = json.loads(data)
                    message = data.get("message", str(ex))
                    if data.get("rc", "") == "KudosUpfront":
                        if self.api_key == ANONYMOUS:
                            message = (
                                _(
                                    f"Register at { REGISTER_STABLE_HORDE_URL } and use your key to improve your rate success. Detail:"
                                )
                                + f" { message }."
                            )
                        else:
                            message = (
                                f"{ HELP_URL } "
                                + _("to learn to earn kudos. Detail:")
                                + f" { message }."
                            )
                except Exception as ex2:
                    show_debugging_data(ex2, "No way to recover error msg")
                    message = str(ex)
                show_debugging_data(message, data)
                if self.api_key == ANONYMOUS and REGISTER_STABLE_HORDE_URL in message:
                    self.informer.show_error(
                        f"{ message }", url=REGISTER_STABLE_HORDE_URL
                    )
                else:
                    self.informer.show_error(f"{ message }")
                return ""
            except URLError as ex:
                show_debugging_data(ex, data)
                self.informer.show_error(
                    _("Internet required, chek your connection: ") + f"'{ ex }'."
                )
                return ""
            except Exception as ex:
                show_debugging_data(ex)
                self.informer.show_error(str(ex))
                return ""

            self.__check_if_ready__()
            images = self.__get_images__()
            images_names = self.__get_images_filenames__(images)

        except HTTPError as ex:
            try:
                data = ex.read().decode("utf-8")
                data = json.loads(data)
                message = data.get("message", str(ex))
                show_debugging_data(ex)
            except Exception as ex3:
                show_debugging_data(ex3)
                message = str(ex)
            show_debugging_data(ex, data)
            self.informer.show_error(_("Stablehorde said: ") + f"'{ message }'.")
            return ""
        except URLError as ex:
            show_debugging_data(ex, data)
            self.informer.show_error(_("Internet required, check your connection"))
            return ""
        except IdentifiedError as ex:
            if ex.url:
                self.informer.show_error(str(ex), url=ex.url)
            else:
                self.informer.show_error(str(ex))
            return ""
        except Exception as ex:
            show_debugging_data(ex)
            self.informer.show_error(_("Service failed with: ") + f"'{ ex }'.")
            return ""
        finally:
            message = self.check_update()
            if message:
                self.informer.show_message(message, url=URL_DOWNLOAD)

        return images_names

    def __inform_progress__(self):
        """
        Reports to informer the progress updating the attribute progress
        with the percentage elapsed time since the job started
        """
        progress = 100 - (int(self.max_time - datetime.now().timestamp()) * self.factor)

        show_debugging_data(f"{progress} {self.progress_text}")

        if self.informer and progress != self.progress:
            self.informer.update_status(self.progress_text, progress)
            self.progress = progress

    def __check_if_ready__(self) -> bool:
        """
        Queries Stable horde API to check if the requested image has been generated,
        returns False if is not ready, otherwise True.
        When the time to get an image has been reached raises an Exception, also
        throws exceptions when there are network problems.

        Calls itself until max_time has been reached or the information from the API
        helps to conclude that the time will be longer than user configured.

        self.id holds the ID of the task that generates the image
        * Uses self.response_data
        * Uses self.check_counter
        * Uses self.max_time
        * Queries self.api_key
        """
        url = f"{ API_ROOT }generate/check/{ self.id }"

        self.__url_open__(url)
        data = self.response_data

        show_debugging_data(data)

        self.check_counter = self.check_counter + 1

        if data["done"]:
            self.progress_text = _("Downloading generated image")
            self.__inform_progress__()
            return True

        if data["processing"] == 0:
            if data["queue_position"] == 0:
                text = _("You are the first in the queue")
            else:
                text = _("Queue position: ") + str(data["queue_position"])
            show_debugging_data(f"Wait time {data['wait_time']}")
        elif data["processing"] > 0:
            text = _("Generating...")
            show_debugging_data(text + f" {self.check_counter} { self.progress }")
        self.progress_text = text

        if self.check_counter < self.check_max:
            if (
                data["processing"] == 0
                and data["wait_time"] + datetime.now().timestamp() > self.max_time
            ):
                # If we are in queue, we will not be served in time
                show_debugging_data(data)
                if self.api_key == ANONYMOUS:
                    message = (
                        _("Get an Api key for free at ")
                        + REGISTER_STABLE_HORDE_URL
                        + _(
                            ".\n This model takes more time than your current configuration."
                        )
                    )
                    raise IdentifiedError(message, url=REGISTER_STABLE_HORDE_URL)
                else:
                    message = (
                        _("Please try with other model,")
                        + f"{self.settings['model']} would take more time than you configured,"
                        + _(" or try again later.")
                    )
                    raise IdentifiedError(message)

            if data["is_possible"] is True:
                # We still have time to wait, given that the status is processing, we
                # wait between 5 secs and 15 secs to check again
                wait_time = min(
                    max(StableHordeClient.CHECK_WAIT, int(data["wait_time"] / 2)),
                    StableHordeClient.MAX_TIME_REFRESH,
                )
                for i in range(1, wait_time * 2):
                    sleep(0.5)
                    self.__inform_progress__()
                self.__check_if_ready__()
                return False
            else:
                show_debugging_data(data)
                raise IdentifiedError(
                    _(
                        "Currently no worker available to generate your image. Please try again later."
                    )
                )
        else:
            if self.api_key == ANONYMOUS:
                message = (
                    _("Get an Api key for free at ")
                    + REGISTER_STABLE_HORDE_URL
                    + _(
                        ".\n This model takes more time than your current configuration."
                    )
                )
                raise IdentifiedError(message, url=REGISTER_STABLE_HORDE_URL)
            else:
                minutes = (self.check_max * StableHordeClient.CHECK_WAIT) / 60
                show_debugging_data(data)
                if minutes == 1:
                    raise IdentifiedError(
                        _(f"Image generation timed out after { minutes } minute.")
                        + _("Please try again later.")
                    )
                else:
                    raise IdentifiedError(
                        _(f"Image generation timed out after { minutes } minutes.")
                        + _("Please try again later.")
                    )
        return False

    def __get_images__(self):
        """
        At this stage Stable horde has generated the images and it's time
        to download them all.
        """
        url = f"{ API_ROOT }generate/status/{ self.id }"
        self.progress_text = _("fetching images")
        self.__inform_progress__()
        self.__url_open__(url)
        data = self.response_data
        show_debugging_data(data)

        return data["generations"]

    def __get_images_filenames__(self, images: list[json]) -> list[str]:
        """
        Downloads the generated images and returns the full path of the
        downloaded images.
        """
        show_debugging_data("Start to download generated images")
        generated_filenames = []
        cont = 1
        nimages = len(images)
        for image in images:
            with tempfile.NamedTemporaryFile(
                "wb+", delete=False, suffix=".webp"
            ) as generated_file:
                if image["img"].startswith("https"):
                    show_debugging_data(f"Downloading { image['img'] }")
                    if nimages == 1:
                        self.progress_text = _("Downloading result")
                    else:
                        self.progress_text = _(
                            f"Downloading image { cont }/{ nimages }"
                        )
                    self.__inform_progress__()
                    with urlopen(image["img"]) as response:
                        bytes = response.read()
                else:
                    show_debugging_data(f"Storing embebed image { cont }")
                    bytes = base64.b64decode(image["img"])

                show_debugging_data(f"Dumping to { generated_file.name }")
                generated_file.write(bytes)
                generated_filenames.append(generated_file.name)
                cont += 1
        if self.warnings:
            message = _(
                "Maybe you need to change some parameters to generate succesfully an image. Horde said:\n * "
            ) + "\n * ".join([i["message"] for i in self.warnings])
            show_debugging_data(self.warnings)
            self.informer.show_error(message, title="warning")
            self.warnings = []
        self.refresh_models()
        return generated_filenames

    def get_settings(self) -> json:
        """
        Returns the stored settings
        """
        return self.settings

    def set_settings(self, settings: json):
        """
        Sets the settings, useful when fetching from a file or updating
        based on user selection.
        """
        self.settings = settings


class HordeClientSettings:
    """
    Store and load settings
    """

    def __init__(self, base_directory: Path = None):
        if base_directory is None:
            base_directory = tempfile.gettempdir()
        self.base_directory = base_directory
        self.settingsfile = "stablehordesettings.json"
        self.file = base_directory / self.settingsfile
        os.makedirs(base_directory, exist_ok=True)

    def load(self) -> json:
        if not os.path.exists(self.file):
            return {"api_key": ANONYMOUS}
        with open(self.file) as myfile:
            return json.loads(myfile.read())

    def save(self, settings: json):
        with open(self.file, "w") as myfile:
            myfile.write(json.dumps(settings))
        os.chmod(self.file, 0o600)


class ProcedureInformation:
    def __init__(
        self,
        model_choices: list[str],
        action: str,
        cache_key: str,
        default_model: str,
        refreshed_date: str = None,
    ):
        self.model_choices = model_choices
        self.action = action
        self.cache_key = cache_key
        self.default_model = default_model
        if refreshed_date is None:
            self.refreshed_date = "2025-07-01"

    # Load the refreshed, stored as
    def update_choices_from(self, choices: json):
        """
        choices is expected to have an structure like:
        { self.cache_key: {"models": [], "date_refreshed_models": "YYYY-MM-DD"} }

        the choices are updated if the structure is present and there are options present
        """
        show_debugging_data(f"fetching choices from {self.cache_key}")
        if self.cache_key not in choices or not choices[self.cache_key]["models"]:
            return
        self.model_choices = choices[self.cache_key]["models"]
        self.refreshed_date = choices[self.cache_key]["date_refreshed_models"]

    def update_choices_into(self, new_choices: json, st_manager: HordeClientSettings):
        """
        updates st_manager with new_settings
        """
        if not new_choices:
            return
        show_debugging_data("storing choices")
        current_choices = st_manager.load()
        if "api_key" in current_choices:
            del current_choices["api_key"]
        current_choices[self.cache_key] = {
            "date_refreshed_models": new_choices["date_refreshed_models"],
            "models": new_choices["models"],
        }
        show_debugging_data(current_choices)
        st_manager.save(current_choices)


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
        show_debugging_data(name)
        show_debugging_data(self.plug_in_procs)
        if name not in self.plug_in_procs:
            return procedure

        self.st_manager = HordeClientSettings(
            Path(Gimp.cache_directory()) / "ikks-py3-stablehorde"
        )
        self.procedures[name].update_choices_from(self.st_manager.load())
        # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
        self.t2i.menu_label = _("_Create Image from Prompt")
        # TRANSLATORS: Dialog title
        self.t2i.dialog_title = _("From Text")
        self.t2i.dialog_description = _("Create an image from a prompt")
        # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
        self.i2i.menu_label = _("_Use Image with Prompt")
        # TRANSLATORS: Dialog title
        self.i2i.dialog_title = _("Use style image")
        self.i2i.dialog_description = _(
            "Create an image from a prompt using the style of the current image"
        )
        # TRANSLATORS: This is the menu, the _ indicates the fast key in the menu
        self.in_paint.menu_label = _("Adjust Image _Region")
        # TRANSLATORS: Dialog title
        self.in_paint.dialog_title = _("Inpaint")
        self.in_paint.dialog_description = _(
            "Replace a deleted portion of the image according to a prompt, make sure you see that part transparent"
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
                    "max-wait-minutes",
                    "seed",
                    "api-key",
                ]
            )
            dialog.fill(controls_to_show)
            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
            else:
                dialog.destroy()

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
                        _("Your image needs to be between 384x384 and 1024x1024.")
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
            drawables = [layer]
            Gimp.Display.new(image)

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
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(_("Your image needs to be between 384x384 and 1024x1024.")),
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
        show_debugging_data(self.bridge.base_info)
        sh_client = StableHordeClient(options, self.bridge.base_info, self.bridge)
        Gimp.progress_init(_("Stable Horde work"))
        try:
            images_names = sh_client.generate_image(options)
        except Exception as ex:
            show_debugging_data(ex)
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error(str(ex)),
            )

        self.display_generated(image, images_names, model)
        message = "The task was succesful"

        new_choices = sh_client.settings.get("local_settings", [])
        show_debugging_data(new_choices)
        self.procedures[procedure_name].update_choices_into(
            new_choices, self.st_manager
        )
        show_debugging_data("Done")
        message += self.bridge.append_success_message
        message += self.bridge.append_warning
        show_debugging_data(message)
        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS, GLib.Error(message)
        )

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

        show_debugging_data("Creating layers")
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
        show_debugging_data("Layers added")
        Gimp.displays_flush()


class GimpUtilitiesBridge(InformerFrontendInterface):
    def __init__(self, procedure: Gimp.ImageProcedure, gimp_version: str):
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

        self.append_warning: str = ""
        self.append_success_message: str = ""

    def set_finished(self):
        Gimp.progress_end()

    def update_status(self, text: str, progress: float = 0.0):
        Gimp.progress_set_text(text)
        Gimp.progress_update(progress / 100.0)

    def show_error(self, message, url="", title="", buttons=0):
        show_debugging_data(url, title)
        if title == "warning":
            self.append_warning += "\n " + message
            return
        raise Exception(message)

    def show_message(self, message, url="", title="", buttons=0):
        self.append_success_message += "\n " + message
        pass

    def get_frontend_property(self, property_name: str) -> str | bool | None:
        try:
            info = Gimp.get_parasite(property_name).get_data()[0]
            return info
        except AttributeError:
            return None

    def set_frontend_property(self, property_name: str, value: str | bool):
        Gimp.attach_parasite(Gimp.Parasite.new(property_name, 0, [value]))

    def path_store_directory(self) -> str:
        pass


Gimp.main(StableDiffusion.__gtype__, sys.argv)

# TBD
#
# * [X] Raise exceptions to be able to report errors
# * [X] Store updated models
# * [X] Also inpainting models
# * [X] Update translations
# * [X] Try async with downlading
# * [ ] Port back to LibreOffice
# * [X] Improve the ticking in the bar
# * [ ] Maybe show warnings
# * [ ] Add a transparent text layer with the information that generated the image:
#    - Prompt, steps, model, and any other information on the invocation.
# * [ ] Use annotations
# * [ ] Locally make outpaint Extend to left, bottom, right, top:
#      - Enlarge Image with a given amount, max 1.024, transparent
#      - Send to process as inpaint
# * [ ] Upscale image locally: Use Image, Scale Image Interpolation Lohab
# cd po && xgettext -o gimp-stable-diffusion.pot --add-comments=TRANSLATORS: --keyword=_ --flag=_:1:pass-python-format --directory=.. gimp-stable-diffusion.py && cd ..
