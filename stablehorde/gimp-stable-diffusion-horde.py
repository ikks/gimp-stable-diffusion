#!/usr/bin/python

# Import necessary libraries/modules
import urllib2  # Import the urllib2 library for making HTTP requests
import tempfile  # Import the tempfile library for working with temporary files
import array    #Import array library 
import os  # Import the os library for file operations
import base64  # Import the base64 library for encoding/decoding data in base64 format
import json  # Import the json library for working with JSON data
import ssl  # Import the ssl library for SSL certificate handling
import sched  # Import the sched library for scheduling tasks
import random # Import RNG
import datetime
import time  # Import the time library for working with time-related functions
import math  # Import the math library for mathematical operations
import gimp  # Import the gimp library
import re  # Import the re library for regular expressions
from gimpfu import *  # Import necessary functions and classes from the gimpfu module

# Define constants and configuration settings
VERSION = 135
INIT_FILE = "init.png"
GENERATED_FILE = "generated.png"
API_ROOT = "https://stablehorde.net/api/v2/"
#md = "Deliberate"
#chosenModel = [md]
# Check interval in seconds
CHECK_WAIT = 5
checkMax = None

#var modelList = (modelReference) => {
   # return Object.keys(modelReference).map(e=>modelReference[e].name) //returns an array of model names
#}

# Configure SSL context to ignore certificate verification (not recommended for production use)
ssl._create_default_https_context = ssl._create_unverified_context

# Define file paths for initialization and generated images
initFile = r"{}".format(os.path.join(tempfile.gettempdir(), INIT_FILE))
generatedFile = r"{}".format(os.path.join(tempfile.gettempdir(), GENERATED_FILE))

# Create a scheduler instance
s = sched.scheduler(time.time, time.sleep)

# Initialize variables for checking update and tracking generation status
checkCounter = 0
id = None

# Function to check for updates
def checkUpdate():
    try:
        # Check if update has been previously checked
        gimp.get_data("update_checked")
        updateChecked = True
    except Exception as ex:
        updateChecked = False

    if updateChecked is False:
        try:
            # Check for updates by fetching version information from a URL
            url = "https://raw.githubusercontent.com/blueturtleai/gimp-stable-diffusion/main/stablehorde/version.json"
            response = urllib2.urlopen(url)
            data = response.read()
            data = json.loads(data)
            gimp.set_data("update_checked", "1")

            if VERSION < int(data["version"]):
                pdb.gimp_message(data["message"])
        except Exception as ex:
            ex = ex

# Function to get image data as base64 encoded string
def getImageData(image, drawable):
    # Save the image as a PNG file
    pdb.file_png_save_defaults(image, drawable, initFile, initFile)
    initImage = open(initFile, "rb")
    encoded = base64.b64encode(initImage.read())
    return encoded

# Function to display generated images
def displayGenerated(images):
    # Get the current foreground color
    color = pdb.gimp_context_get_foreground()
    # Set foreground color to black
    pdb.gimp_context_set_foreground((0, 0, 0))

    for image in images:
        if re.match("^https.*", image["img"]):
            response = urllib2.urlopen(image["img"])
            bytes = response.read()
        else:
            bytes = base64.b64decode(image["img"])

        imageFile = open(generatedFile, "wb+")
        imageFile.write(bytes)
        imageFile.close()

        imageLoaded = pdb.file_webp_load(generatedFile, generatedFile)
        pdb.gimp_display_new(imageLoaded)
        # Add text to the generated image
        pdb.gimp_text_fontname(imageLoaded, None, 2, 2, str(image["seed"]), -1, TRUE, 12, 1, "Sans")
        pdb.gimp_image_set_active_layer(imageLoaded, imageLoaded.layers[1])

    # Restore the original foreground color
    pdb.gimp_context_set_foreground(color)
    return

# Function to get generation status from the API
def getImages():
    url = API_ROOT + "generate/status/" + id
    response = urllib2.urlopen(url)
    data = response.read()
    data = json.loads(data)
    return data["generations"]

# Function to check the generation status
def checkStatus():
    url = API_ROOT + "generate/check/" + id
    response = urllib2.urlopen(url)
    data = response.read()
    data = json.loads(data)

    global checkCounter
    checkCounter = checkCounter + 1

    if data["processing"] == 0:
        text = "Queue position: " + str(data["queue_position"]) + ", Wait time: " + str(data["wait_time"]) + "s"
    elif data["processing"] > 0:
        text = "Generating..."

    # Set progress text
    pdb.gimp_progress_set_text(text)

    if checkCounter < checkMax and data["done"] is False:
        if data["is_possible"] is True:
            # Schedule the next status check
            s.enter(CHECK_WAIT, 1, checkStatus, ())
            s.run()
        else:
            raise Exception("Currently no worker available to generate your image. Please try again later.")
    elif checkCounter == checkMax:
        minutes = (checkMax * CHECK_WAIT) / 60
        raise Exception("Image generation timed out after " + str(minutes) + " minutes. Please try again later.")
    elif data["done"] == True:
        return

# Main function for generating images
def generate(image, drawable, mode, models, initStrength, promptStrength, steps, seed, nsfw, censor_nsfw, prompt, apikey, maxWaitMin):
     
    mod = [models]
    
    

    
    # Validate image size
    if image.width < 384 or image.width > 1024 or image.height < 384 or image.height > 1024:
        raise Exception("Invalid image size. Image needs to be between 384x384 and 1024x1024.")

    # Validate prompt input
    if prompt == "":
        raise Exception("Please enter a prompt.")

    # Validate image mode and alpha channel for inpainting
    if mode == "MODE_INPAINTING" and drawable.has_alpha == 0:
        raise Exception("Invalid image. For inpainting, an alpha channel is needed.")

    # Initialize GIMP progress
    pdb.gimp_progress_init("", None)

    global checkMax
    checkMax = (maxWaitMin * 60) / CHECK_WAIT

    try:
        params = {
            "cfg_scale": float(promptStrength),
            "steps": int(steps),
            "seed": seed
        }

        data = {
            "params": params,
            "prompt": prompt,
            "nsfw": nsfw,
            "censor_nsfw": censor_nsfw,
            "models": mod,
            "r2": True
            
            

        }

        # Adjust image dimensions to be multiples of 64
        if image.width % 64 != 0:
            width = math.floor(image.width / 64) * 64
        else:
            width = image.width

        if image.height % 64 != 0:
            height = math.floor(image.height / 64) * 64
        else:
            height = image.height

        params.update({"width": int(width)})
        params.update({"height": int(height)})

        if mode == "MODE_IMG2IMG":
            init = getImageData(image, drawable)
            data.update({"source_image": init})
            data.update({"source_processing": "img2img"})
            data.update({"models": mod})
            params.update({"denoising_strength": (1 - float(initStrength))})
        elif mode == "MODE_INPAINTING":
            init = getImageData(image, drawable)
            models = ["Deliberate Inpainting"]
            data.update({"source_image": init})
            data.update({"source_processing": "inpainting"})
            data.update({"models": mod})
        
        
        
        
        
        data = json.dumps(data)

        apikey = "0000000000" if not apikey else apikey

        headers = {"Content-Type": "application/json", "Accept": "application/json", "apikey": apikey}
        url = API_ROOT + "generate/async"

        request = urllib2.Request(url=url, data=data, headers=headers)

        response = urllib2.urlopen(request)
        data = response.read()

        try:
            data = json.loads(data)
            global id
            id = data["id"]
        except Exception as ex:
            raise Exception(data)

        # Check and display generation status
        checkStatus()
        images = getImages()
        displayGenerated(images)

    except urllib2.HTTPError as ex:
        try:
            data = ex.read()
            data = json.loads(data)

            if "message" in data:
                message = data["message"]
            else:
                message = str(ex)
        except Exception:
            message = str(ex)

        raise Exception(message)
    except Exception as ex:
        raise ex
    finally:
        # End GIMP progress
        pdb.gimp_progress_end()
        # Check for updates
        checkUpdate()

    return

# Register the GIMP plugin with the specified parameters
register(
    "stable-diffusions-horde",
    "stable diffuesion horde Gimp Plugin",
    "stable-horde",
    "Unkn0wnable",
    "Unkn0wnable",
    "2023",
    "<Image>/AI/Stablehorde",
    "*",
    [
        (PF_RADIO, "mode", "Generation Mode", "MODE_TEXT2IMG", (
            ("Text -> Image", "MODE_TEXT2IMG"),
            ("Image -> Image", "MODE_IMG2IMG"),
            ("Inpainting", "MODE_INPAINTING")
        )),
        (PF_STRING,  "md", "Select Model","[]"), 
        (PF_SLIDER, "initStrength", "Init Strength", 0.3, (0, 1, 0.1)),
        (PF_SLIDER, "promptStrength", "Prompt Strength", 8, (0, 20, 1)),
        (PF_SLIDER, "steps", "Steps", 25, (10, 150, 1)),
        (PF_STRING, "seed", "Seed (optional)", "-1"),
        (PF_TOGGLE, "nsfw", "NSFW", False),
        (PF_TOGGLE, "censor_snfw", "Censor NSFW", TRUE),
        (PF_STRING, "prompt", "Prompt", ""),
        (PF_STRING, "apiKey", "API key (optional)", ""),
        (PF_SLIDER, "maxWaitMin", "Max Wait (minutes)", 10, (1, 10, 1))
    ],
    [],
    generate
)

# Call the main GIMP function to start the plugin
main()
