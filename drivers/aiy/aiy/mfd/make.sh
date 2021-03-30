#!/bin/bash
DIR=$(dirname $(realpath $0))
SPACEPARK=${DIR}/../../../..
pushd ${DIR}
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/mfd clean
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/mfd CONFIG_AIY_IO_I2C=m  modules
popd
