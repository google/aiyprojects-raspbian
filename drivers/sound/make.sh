#!/bin/bash
DIR=$(dirname $(realpath $0))
SPACEPARK=${DIR}/../..
pushd ${DIR}

make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/sound clean

make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/sound CONFIG_GPIO_AIY_IO=m  modules

popd
