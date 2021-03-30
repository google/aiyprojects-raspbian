#!/bin/bash
DIR=$(dirname $(realpath $0))
SPACEPARK=${DIR}/../../../../..
pushd ${DIR}
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/staging/myriad clean
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/staging/myriad CONFIG_AIY_VISION=m modules
popd

