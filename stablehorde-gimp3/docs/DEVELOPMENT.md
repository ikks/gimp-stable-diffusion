# Developing with Gimp

Gimp2 series is not being longer developed.

For Gimp3 series, the source code is in stablehorde-gimp3/gimp-stable-diffusion.py
the three menu entries are there, we avoid to use
dependencies out of the common library.

Please use a formatter and align with pep8, also help is welcome on typing,
we try to support python3.8 and upwards.  The same code for the http
client is being used for
[libreoffice plugin](https://github.com/ikks/libreoffice-stable-diffusion).

## Changes from Gimp2 Series

* We use thread and asyncio to have an interface that allows continue
  working in other things while the images are generated
* We use gettext to have translations, see [CONTRIBUTING](CONTRIBUTING#Translating). 
* When an image had a prompt that conducted to a censored one we show
  a warning instead of an image telling it.
* If the process is interrupted or there is a timeout and the image is
  being processed by the horde, a layer is created to refer to the
  url to download the image manually.
* Attribution on metadata is automatically stored when an image is
  generated.

## Gimp3 python console helps to work interactively

To get first image being edited

```python
image = Gimp.get_images()[0]
```

Afterwards is possible to use

```python
help(image)
```

and use the documentation reference

# Reference

## With Debian

The documentation is available locally with

```
sudo apt install -y libgimp-3.0-doc
cd /usr/share/doc/libgimp-3.0-doc/reference/gimp-3.0/
python -m http.server
# visit http://localhost:8000/libgimp-3.0/
# visit http://localhost:8000/libgimpui-3.0/
```
