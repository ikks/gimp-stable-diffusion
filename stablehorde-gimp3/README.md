
# gimp-stable-diffusion-horde

This repository includes a [GIMP](https://gimp.org) plugin to make
use of [StableHorde](https://stablehorde.net). Stablehorde is a
cluster of stable-diffusion servers run by volunteers. You can create
stable-diffusion images for free without running a colab notebook
or a local server. Please check the section
[Limitations](README#Limitations) to better understand where the
limits are.

The latest changes are tracked in [Changelog](CHANGELOG), and for
historic purposes you can check [HISTORY.md](/stablehorde/HISTORY.md).

## Installation
### Download Plugin

Download the [latest release](https://github.com/ikks/gimp-stable-diffusion/releases/).

### GIMP

To run this plugin GIMP 3.X is needed.

1. Start GIMP and open the preferences dialog via "edit/preferences"
and scroll down to "folders". Expand "folders" and click on
"plug-ins". Select the folder which includes your username and open
your file manager there.



https://github.com/user-attachments/assets/aec71b81-b410-45e5-9654-294df9dadd84



2. Unzip the downloaded file in your `plug-ins` folder. If
you are on MacOS or Linux, change the file permissions to 764, leave
the permissions of the directory as they are.

You will end up with a structure like:

```
plug-ins
└── gimp-stable-diffusion
   ├── gimp-stable-diffusion.py
   └── locale
       └── es
           └── LC_MESSAGES
               └── gimp-stable-diffusion.mo
```

3. Restart GIMP. You should now see the new menu "AI". If you
don't see this, something went wrong. Please check in this case
[Troubleshooting/GIMP](#gimp-1) for possible solutions. The menu has one item
`Stable Horde` with three submenus.  You can start creating images
right away.

<img width="1366" height="768" alt="screenshot-2025-08-05-195704" src="https://github.com/user-attachments/assets/81b23599-ef36-46c7-92ab-7038989cdcea" />


## Generate images
Now we are ready to generate images.

1. On GIMP create/open an image with a size between 388x388 and
1024x1024. The generated image will have the size of the opened image
or a bit smaller. Check below for an explanation.
   - Stable diffusion only generates image sizes which are multiple of
   64. This means, if your image has a size of 650x512, the generated
   image will have a size of 640x512.
   - The larger the image, the longer you have to wait for
   generation. The reason is, that all servers in the cluster support
   388x388, but not all larger sizes.

2. Select the new `AI/Stable Horde` menu item. You will see three options.
  - Adjust Image Region
  - Create Image from Prompt
  - Use Image with Prompt

<details>
  <summary>Details on using the plugin</summary>

- **Prompt:** How the generated image should look like.

- **Prompt Strength:** How much the AI should follow the prompt. The
higher the value, the more the AI will generate an image which looks
like your prompt. 7.5 is a good value to use.

- **Steps:** How many steps the AI should use to generate the
image. The higher the value, the more the AI will work on details. But
it also means, the longer the generation takes and the more the GPU
is used. 50 is a good value to use.

- **NSFW:** If you want to send a prompt, which is excplicitly NSFW
(Not Safe For Work).
    - If you flag your request as NSFW, only servers, which accept
    NSFW prompts, work on the request. It's very likely, that it
    takes then longer than usual to generate the image. If you don't
    flag the prompt, but it is NSFW, you will receive a black image.
    - If you didn't flag your request as NSFW and don't prompt NSFW,
    you will receive in some cases a black image, although it's not
    NSFW (false positive). Just rerun the generation in that case.

- **Max Wait:** The maximum time in minutes you want to wait until
image generation is finished. When the max time is reached, a timeout
happens and the generation request is stopped.

- **Seed:** This parameter is optional. If it is empty, a random seed
will be generated on the server. If you use a seed, the same image is
generated again in the case the same parameters for init strength,
steps, etc. are used. A slightly different image will be generated,
if the parameters are modified. You find the seed in an additional
layer at the top left.

- **API key:** This parameter is optional. If you don't enter an
API key, you run the image generation as anonymous. The downside
is, that you will have then the lowest priority in the generation
queue. For that reason it is recommended registering for free on
[StableHorde](https://stablehorde.net) and getting an API key.

### Inpaint

When you are replacing a portion of an image, you can choose also

- **# of Images:** Stating the number of intermediate images to
be generated from the original one to the final result.

### Use Image in Prompt

This feature ais to use an original image as style for the final
one and the prompt is the intent of the final image.

- **Init Strength:** How much the AI should take the init image into
account. The higher the value, the more will the generated image will
follow the style of the initial image. 0.3 is a good value to use.

</details>
  
3. Click on the OK button. The values you inserted into the dialog
will be transmitted to the server, which dispatches the request now to
one of the stable-diffusion servers in the cluster. Your generation
request is added to queue. You can see the queue position and the
remaining wait time in the status bar of the dialog. When the image
has been generated successfully, it will be shown as a new image in
GIMP. The used seed is shown at the top left in an additional layer.

<img width="1366" height="768" alt="screenshot-2025-08-05-195902" src="https://github.com/user-attachments/assets/964e5181-e410-40e4-9c17-f738449985b1" />

## Inpainting
Inpainting means replacing a part of an existing image. For example if
you don't like the face on an image, you can replace it. **Inpainting
is currently still in experimental stage. So, please don't expect
perfect results.** The experimental stage is caused by the server
side and not by GIMP.

For inpainting it's necessary to prepare the input image because the
AI needs to know which part you want to replace. For this purpose
you replace this image part by transparency. To do so, open the init
image in GIMP and select "Layer/Transparency/Add alpha channel". Select
now the part of the image which should be replaced and delete it. You
can also use the eraser tool.

For the prompt you use now a description of the new image. For example
the image shows currently "a little girl running over a meadow with
a balloon" and you want to replace the balloon by a parachute. You
just write now "a little girl running over a meadow with a parachute".

## Limitations
- **Generation speed:** StableHorde is a cluster of stable-diffusion
servers run by volunteers. The generation speed depends on how many
servers are in the cluster, which hardware they use and how many others
want to generate with StableHorde. The upside is, that StableHorde is
free to use, the downside that the generation speed is unpredictable.

- **Privacy:** The privacy StableHorde offers is similar to generating
in a public discord channel. So, please assume, that neither your
prompts nor your generated images are private.

- **Features:** Currently text2img, img2img and inpainting are
supported. As soon as StableHorde supports outpainting, this will be
available in the plugin too.

### Timeouts

Sometimes when images are taking too long to be generated and they are
in process with the workers, the plugin will tell you that the timeout
setting has been reached or will be reached given that you are in a
queue and the expected time is long.

The popup will give you an address to visit, also you will have a
[textlayer](https://docs.gimp.org/3.0/en/gimp-image-text-management.html)
whose name is a URL that you can use with your browser to checkout
the status of the process and eventually, when you visit the url,
inside it there can be one or more urls that you can follow to reach
the image, it can be saved as a
[webp image](https://en.wikipedia.org/wiki/WebP) and opened in Gimp,
libreoffice or the one that suit your needs.

If there is not a TextLayer, is because Gimp already has the image or
maybe it was not possible to generate the desired image. With an
[API Key](https://aihorde.net/register) there are more chances to get
an image generated than without having one, and with
[more kudos](https://aihorde.net/faq), more priority.

## Troubleshooting
### GIMP
#### AI menu is not shown
##### Linux

* If you get the error ```gimp: LibGimpBase-WARNING: gimp:
gimp_wire_read(): error```, it's very likely, that you have a GIMP
version installed which doesn't include Python. Check if you have
got the menu "Help > Search and Run a Command". Type `Python`, If
`Python Console` is missing, please
install GIMP from [here](https://www.gimp.org/downloads/)
* Please try https://flathub.org/apps/details/org.gimp.GIMP if you
have got any other problems.

##### macOS

* Please double check if the permissions of the plugin py file are set
to 764. It seems, that changing permissions doesn't work via the file
manager. Please open a terminal, cd to the plugins directory and run
"chmod u+x *py".

##### macOS/Linux

* Open a terminal and try to run the plugin py file manually via
```python <path-to-plugin-folder>/gimp-stable-diffusion/gimp-stable-diffusion.py```.
You should see the error message, that "gimpfu" is unknown. Make sure,
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

**Where is the scaler that was in Gimp2 series?** It's possible to
use the key `/` and look for Scale Image, choose Interpolation: LoHalo.

## Contributing

[docs/CONTRIBUTING.md] holds the detail on how to improve the plugin.

## Internals

**How do I troubleshot myself?** Open gimp from a terminal and look
at the output it gives.  You can turn on DEBUG editing the plugin file
`gimp-stable-diffusion.py` and changing `DEBUG = False` to
`DEBUG = True` (case matters).

## References and other options

* [Gimp](https://gimp.org): The GNU image manipulation program
* [StableHorde](https://stablehorde.net): A collaborative network to share resources
* More indepth explanation of options and use cases from a
[similar
plugin](https://opencreativecloud.com/gimp-stable-diffusion-integration/)
* [Local Plugin](https://github.com/kritiksoman/GIMP-ML)
* Background remover [Local on Linux](https://github.com/manu12121999/GIMP-Background-Remover)
* [Openvino plugins](https://github.com/intel/openvino-ai-plugins-gimp)
