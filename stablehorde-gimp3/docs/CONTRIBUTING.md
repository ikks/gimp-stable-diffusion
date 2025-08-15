# How to contribute

Filling an issue is one way, sending a pull request, translating
or suggesting a feature. Also if you would like, please contact
the author to buy him a coffee.

## Translating

If you wish to help with a translation, please submit an
[issue](https://github.com/ikks/gimp-stable-diffusion/issues)
indicating it.

Steps are usually:

1. [File an issue](https://github.com/ikks/gimp-stable-diffusion/issues)
  telling it so, to avoid reprocess.
1. Clone the repository
1. Edit the files
1. Make the pull request

There is only need to translate one file per language for the plugin.

Through the rest of this document, we use xxx language as a sample, identified
by `xx`, replace for your real language.

When you open the issue, you can copy the file `po/gimp-stable-diffusion.pot`
to `po/xx.po` and use a tool like [poedit](https://poedit.net/) or the one you
prefer to make the translation of `po/xx.po`.

### Checking your translation

It's possible to use the program `msgfmt` to check for possible errors
in a .po file, which is part of
[gettext](https://www.gnu.org/software/gettext).

Once you have gettext installed it's possible to check and test the
translation with:

```
msgfmt -cv po/es.po
```

This tells you if there are errors and in which line, it will generate
a .mo file that is the one used.

if you also have `make` installed, it will be possible to use the
Makefile to do things for you.

### Using your translation

Run `make update_translations` and if you are on Mac or Linux, you can
issue `make install`, reopen Gimp and you will have the translations in
place.

The `po/xx.po` with a successfull `make update_translations` will create
`locale/xx/LC_MESSAGES/gimp-stable-diffusion.mo`

### PR (Pull Request)

Before [PRing], please use an spell checker to make sure there isn't a typo
or something that can lower your personal signature. You can also
attach your .po file if you prefer, so I can incorporate it.

Thanks for helping with it.


