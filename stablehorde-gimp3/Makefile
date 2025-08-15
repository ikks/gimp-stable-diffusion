# A good gettext explanation
# https://www.labri.fr/perso/fleury/posts/programming/a-quick-gettext-tutorial.html
#
# To prepare a new language with locale lo
# msginit --input=po/gimp-stable-diffusion.pot --locale=lo --output=po/lo.po

EXEC=gimp-stable-diffusion
LANG=es
INSTALL_DIR=~/.config/GIMP/3.0/plug-ins
PO_FILES := $(wildcard po/*.po)
MO_FILES := $(subst .po,/LC_MESSAGES/$(EXEC).mo, $(subst po/,locale/,$(PO_FILES)))

all: $(EXEC).zip

locale/%/LC_MESSAGES/$(EXEC).mo: po/%.po po/$(EXEC).pot
	mkdir -p $(dir $@)
	msgfmt --output-file=$@ $<

po/$(LANG).po: po/$(EXEC).pot
	msgmerge --update $@ $<

po/$(EXEC).pot: $(EXEC).py
	xgettext -o $@ --add-comments=TRANSLATORS: --keyword=_ --flag=_:1:pass-python-format --directory=. $<

$(EXEC).zip: $(EXEC).py
	zip -r $(EXEC).zip $(EXEC)

clean:
	rm -rf  locale/ po/*~ $(EXEC).zip

initlang:
	msginit --input=po/gimp-stable-diffusion.pot --locale=$(LANG) --output=po/$(LANG).po

install:
	mkdir -p $(INSTALL_DIR)/$(EXEC)/locale
	cp -rf locale/* $(INSTALL_DIR)/$(EXEC)/locale
	cp $(EXEC).py $(INSTALL_DIR)/$(EXEC)
	chmod +x $(INSTALL_DIR)/$(EXEC)/$(EXEC).py

publish:
	mkdir -p $(EXEC)
	cp -r $(EXEC).py locale $(EXEC) 
	zip -r $(EXEC).zip $(EXEC)
	scripts/publish

update_translations:
	make po/$(EXEC).pot
	for file in $(MO_FILES); do make $$file; done 

.PHONY: clean initlang install publish

# Gimp plugin locale structure is
# ├── locale
# │   └── es
# │       └── LC_MESSAGES
# └── po

