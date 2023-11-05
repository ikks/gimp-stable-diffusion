#!/usr/bin/env python

from gimpfu import *

def upscale_image(image, drawable, scale_factor):
    # Check the scale factor range
    if not (1 <= scale_factor <= 4):
        raise ValueError("Scale factor must be between 1 and 4")

    # Set the interpolation method to Lanczos (best for upscaling)
    pdb.gimp_context_set_interpolation(INTERPOLATION_LANCZOS)

    # Calculate the new dimensions
    new_width = int(drawable.width * scale_factor)
    new_height = int(drawable.height * scale_factor)

    # Scale the image
    pdb.gimp_image_scale(image, new_width, new_height)

register(
    "stabel-horde-diffusion-upscaler",
    "Stable Horde Upscaler",
    "stablehorde",
    "Unkn0wnable", "Unkn0wnable", "2023",
    "<Image>/AI/Stablehorde/Upscale",
    "*", # Image types
    [
        (PF_SPINNER, "scale_factor", "Scale Factor", 2, (1, 4, 0.1)), # Spinner with range from 1 to 4 and step 0.1
    ],
    [],
    upscale_image
)

main()
