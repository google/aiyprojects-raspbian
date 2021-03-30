#!/bin/bash
DIR=$(dirname $(realpath $0))
SPACEPARK=${DIR}/../../../..
pushd ${DIR}
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/pwm clean
make -C ${SPACEPARK}/raspberrypi-linux ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- \
  SUBDIRS=${SPACEPARK}/drivers-raspi/aiy/aiy/pwm CONFIG_PWM_AIY_IO=m modules
popd
