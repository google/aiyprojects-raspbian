#!/bin/bash
DIR=$(dirname $(realpath $0))
SPACEPARK=${DIR}/../../../../..
pushd ${DIR}
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/iio/adc clean
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/iio/adc CONFIG_AIY_ADC=m  modules
popd
