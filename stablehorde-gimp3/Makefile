# A good gettext explanation
# https://www.labri.fr/perso/fleury/posts/programming/a-quick-gettext-tutorial.html
#
# To prepare a new language with locale lo
# msginit --input=po/gimp-stable-diffusion.pot --locale=lo --output=po/lo.po

EXEC=gimp-stable-diffusion
LANG=es
INSTALL_DIR=~/.config/GIMP/3.0/plug-ins
PO_FILES := $(wildcard po/[a-z][a-z].po)
PO_FULL_FILES := $(subst po/,po/full.,$(PO_FILES))
MO_FILES := $(subst .po,/LC_MESSAGES/$(EXEC).mo, $(subst po/,locale/,$(PO_FILES)))

all: $(EXEC).zip

locale/%/LC_MESSAGES/$(EXEC).mo: po/full.%.po
	mkdir -p $(dir $@)
	msgfmt --output-file=$@ $<

po/full.%.po: po/%.po modules/aihordeclient/po/%.po
	msgcat -o $@ $^

po/$(LANG).po: po/$(EXEC).pot
	msgmerge -q --update $@ $<

po/$(EXEC).pot: $(EXEC).py
	xgettext -o $@ --add-comments=TRANSLATORS: --keyword=_ --flag=_:1:pass-python-format --directory=. $<

$(EXEC).zip: $(EXEC).py $(MO_FILES)
	mkdir -p $(EXEC)/module
	cp -r $(EXEC).py locale $(EXEC)
	cp modules/aihordeclient/src/aihordeclient/__init__.py $(EXEC)/module/aihordeclient.py
	zip -r $(EXEC).zip $(EXEC)

clean:
	rm -rf  $(MO_FILES) po/*~ po/*bak $(EXEC).zip po/full.*

initlang:
	msginit --input=po/gimp-stable-diffusion.pot --locale=$(LANG) --output=po/$(LANG).po

install: $(MO_FILES)
	rm -rf $(INSTALL_DIR)/$(EXEC)/module
	mkdir -p $(INSTALL_DIR)/$(EXEC)/locale $(INSTALL_DIR)/$(EXEC)/module
	cp -rf locale/* $(INSTALL_DIR)/$(EXEC)/locale
	cp modules/aihordeclient/src/aihordeclient/__init__.py $(INSTALL_DIR)/$(EXEC)/module/aihordeclient.py
	cp $(EXEC).py $(INSTALL_DIR)/$(EXEC)
	chmod +x $(INSTALL_DIR)/$(EXEC)/$(EXEC).py

publish: $(EXEC).zip
	scripts/publish

langs: po/$(EXEC).pot $(PO_FULL_FILES) $(MO_FILES)
	postats po/*.po

.PHONY: clean initlang install publish update_translation

# Gimp plugin locale structure is
# ├── locale
# │   └── es
# │       └── LC_MESSAGES
# └── po

