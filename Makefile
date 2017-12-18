PI ?= raspberrypi.local

SHORTCUTS = $(wildcard shortcuts/*.desktop)

check:
	PYTHONPATH=$$PWD/src python3 -m unittest discover tests

deploy_scripts:
	git ls-files | rsync -avz --exclude=".*" --exclude="*.desktop" --files-from - . pi@$(PI):~/AIY-projects-python

deploy_shortcuts:
	scp $(SHORTCUTS) pi@$(PI):~/Desktop

deploy: deploy_scripts deploy_shortcuts
