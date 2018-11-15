# Changelog

All SD card images can be found at [releases][github-releases] page.

## AIY Kits Release 2018-11-16

Compatible with Voice HAT, Voice Bonnet, and Vision Bonnet.

**Fixes**

* Fix tts engine click sound
* Fix `assistant_grpc_demo.service`: add DISPLAY environment variable and proper
systemd dependencies
* Fix various linter findings: python3 compatibility, wrong variable names, etc.

**Improvements**

* New `board.py` to access button and LED on all boards
* New audio API in `voice/audio.py`
* Direct python support for iNaturalist models
* Load anchors/labels directly from text files
* Add `get_inference_state()` and `resest()` to Vision Bonnet protocol
* Add Voice HAT schematic in `docs` folder
* Add sparse representation for output tensors to increase data transfer rate
* SVG-image overlay for video streaming (experimental)

## AIY Kits Release 2018-08-03

Compatible with Voice HAT, Voice Bonnet, and Vision Bonnet.

**Fixes**

* Fix PulseAudio infinite loop with Voice Bonnet
* Fix PulseAudio volume control
* Fix gpiozero LED on/off bug
* Fix local USB networking on macOS, no driver required
* Fix check_audio.py

**Improvements**

* Add Makefile for common shortcuts
* Add vision unit tests for all models and examples
* Add video streaming support (experimental)
* Add Google Cloud IoT support (experimental)
* Add more documentation (pinouts, drivers, troubleshooting, etc.)
* Add new code examples and update existing ones
* Add CHANGES.md to track release changes
* Remove unnecessary files (e.g. ALSA configs)
* Update vision driver to support mmap syscall
* Update sound driver to support latest Raspbian image
* Update HACKING.md

## AIY Kits Release 2018-04-13

Compatible with Voice HAT, Voice Bonnet, and Vision Bonnet.

## AIY Kits Release 2018-02-21

Compatible with Voice HAT, Voice Bonnet, and Vision Bonnet.

## AIY Kits Release 2017-12-18

Compatible with Voice HAT and Vision Bonnet.

## VoiceKit Classic Image 2017-09-11

Compatible with Voice HAT.

[github-releases]: https://github.com/google/aiyprojects-raspbian/releases