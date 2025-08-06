# A good gettext explanation
# https://www.labri.fr/perso/fleury/posts/programming/a-quick-gettext-tutorial.html
#
# To prepare a new language with locale lo
# msginit --input=po/gimp-stable-diffusion.pot --locale=lo --output=po/lo.po

EXEC=gimp-stable-diffusion
LANG=es
INSTALL_DIR=~/.config/GIMP/3.0/plug-ins

all: locale/$(LANG)/LC_MESSAGES/$(EXEC).mo

locale/$(LANG)/LC_MESSAGES/$(EXEC).mo: po/$(LANG).po
	msgfmt --output-file=$@ $<

po/$(LANG).po: po/$(EXEC).pot
	msgmerge --update $@ $<

po/$(EXEC).pot: $(EXEC).py
	xgettext -o po/$(EXEC).pot --add-comments=TRANSLATORS: --keyword=_ --flag=_:1:pass-python-format --directory=. gimp-stable-diffusion.py

publish:
	mkdir -p $(EXEC)
	cp -r $(EXEC).py locale $(EXEC) 
	zip -r $(EXEC).zip $(EXEC)

clean:
	@rm -rf  locale/$(LANG)/LC_MESSAGES/$(EXEC).mo po/*~ $(EXEC)

structure:
	mkdir -p po locale/$(LANG)/LC_MESSAGES

initlang:
	msginit --input=po/gimp-stable-diffusion.pot --locale=$(LANG) --output=po/$(LANG).po

install:
	mkdir -p $(INSTALL_DIR)/$(EXEC)/locale/$(LANG)/LC_MESSAGES/
	cp locale/$(LANG)/LC_MESSAGES/$(EXEC).mo $(INSTALL_DIR)/$(EXEC)/locale/es/LC_MESSAGES
	cp $(EXEC).py $(INSTALL_DIR)/$(EXEC)
	chmod +x $(INSTALL_DIR)/$(EXEC)/$(EXEC).py

.PHONY: clean structure

# Gimp plugin locale structure is
# ├── locale
# │   └── es
# │       └── LC_MESSAGES
# └── po

