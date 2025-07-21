
# gimp-stable-diffusion-horde

This repository includes a [GIMP](https://gimp.org) plugin to make
use of [StableHorde](https://stablehorde.net). Stablehorde is a
cluster of stable-diffusion servers run by volunteers. You can create
stable-diffusion images for free without running a colab notebook
or a local server. Please check the section "Limitations" to better
understand where the limits are.

Please check [HISTORY.md](/stablehorde/HISTORY.md) for the latest
changes.

## Installation
### Download Plugin

Download [gimp-stable-diffusion.py](https://github.com/ikks/gimp-stable-diffusion/blob/gimp3/stablehorde-gimp3/gimp-stable-diffusion.py).

### GIMP

To run this plugin GIMP 3.X is needed.

1. Start GIMP and open the preferences dialog via "edit/preferences"
and scroll down to "folders". Expand "folders" and click on
"plug-ins". Select the folder which includes your username and open
your file manager there.

2. Create a folder called `gimp-stable-diffusion` and paste
`gimp-stable-diffusion.py` from the repository into this directory. If
you are on MacOS or Linux, change the file permissions to 764, leave
the permissions of the directory as they are.

You would end up with a structure like:
```
..
└── plug-ins
    └── gimp-stable-diffusion
        └── gimp-stable-diffusion.py
```

3. Restart GIMP. You should now see the new menu "AI". If you
don't see this, something went wrong. Please check in this case
"Troubleshooting/GIMP" for possible solutions. The menu has one item
`Stable Horde`. This item can't currently be selected. This will work
once you have an image open. More about this below.

## Generate images
Now we are ready for generating images.

1. On GIMP create/open an image with a size between 388x388 and
1024x1024. The generated image will have the size of the opened image
or a bit smaller. Check below for an explanation.
   - Stable diffusion only generates image sizes which are multiple of
   64. This means, if your image has a size of 650x512, the generated
   image will have a size of 640x512.
   - The larger the image, the longer you have to wait for
   generation. The reason is, that all servers in the cluster support
   388x388, but not all larger sizes.

2. Select the new AI/Stablehorde menu item. You will see three options.
  - Text -> Image
  - Image -> Image
  - Inpainting
  
## Troubleshooting
### GIMP
#### AI menu is not shown
##### Linux

* If you get the error ```gimp: LibGimpBase-WARNING: gimp:
gimp_wire_read(): error```, it's very likely, that you have a GIMP
version installed, which doesn't include Python. Check, if you have
got the menu "Filters > Python-Fu > Console". If it is missing, please
install GIMP from here: https://flathub.org/apps/details/org.gimp.GIMP.
* Please try https://flathub.org/apps/details/org.gimp.GIMP if you
have got any other problems.

##### macOS

* Please double check if the permissions of the plugin py file are set
to 764. It seems, that changing permissions doesn't work via the file
manager. Please open a terminal, cd to the plugins directory and run
"chmod u+x *py".

##### macOS/Linux

* Open a terminal and try to run the plugin py file manually via
```python <path-to-plugin-folder>/gimp-stable-diffusion.py```. You
should see the error message, that "gimpfu" is unknown. Make sure,
that you are running Python3, as this version is used by GIMP. If
other errors occur, please reinstall GIMP.

## FAQ

**Why is the generated image smaller than the opened image?**
Stable-diffusion only generates image sizes which are multiple of
64. This means, if your opened image has a size of 650x512, the
generated image will have a size of 640x512.

**Where can I find the GIMP 2 plugin?** Take a look at
[stablehorde](../stablehorde/README.md)

**Will outpainting be supported?** This depends on which features
the StableHorde cluster supports.

**How do I report an error or request a new feature?** Please open
a new issue in this repository.
