#!/bin/bash

set -o xtrace
set -o errexit

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DTC_ARGS="-W no-unit_address_vs_reg -@ -O dtb"

pushd ${SCRIPT_DIR}/vision
dtc ${DTC_ARGS} -o /boot/overlays/aiy-visionbonnet.dtbo aiy-visionbonnet-overlay.dts
dtc ${DTC_ARGS} -o /boot/overlays/aiy-leds-vision.dtbo aiy-leds-vision-overlay.dts
dtc ${DTC_ARGS} -o /boot/overlays/aiy-io-vision.dtbo aiy-io-vision-overlay.dts
popd

pushd ${SCRIPT_DIR}/voice
dtc ${DTC_ARGS} -o /boot/overlays/aiy-voicebonnet.dtbo aiy-voicebonnet-overlay.dts
dtc ${DTC_ARGS} -o /boot/overlays/aiy-leds-voice.dtbo aiy-leds-voice-overlay.dts
dtc ${DTC_ARGS} -o /boot/overlays/aiy-io-voice.dtbo aiy-io-voice-overlay.dts
popd
