#!/bin/bash
DIR=$(dirname $(realpath $0))
SPACEPARK=${DIR}/../../../..
pushd ${DIR}
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/gpio clean
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/gpio CONFIG_GPIO_AIY_IO=m  modules
popd
