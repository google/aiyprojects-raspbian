#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 1>&2
   exit 1
fi

set -e

sed -i \
  -e "s/^dtparam=audio=on/#\0/" \
  -e "s/^#\(dtparam=i2s=on\)/\1/" \
  /boot/config.txt
grep -q "dtoverlay=i2s-mmap" /boot/config.txt || \
  echo "dtoverlay=i2s-mmap" >> /boot/config.txt
grep -q "dtoverlay=googlevoicehat-soundcard" /boot/config.txt || \
  echo "dtoverlay=googlevoicehat-soundcard" >> /boot/config.txt
grep -q "dtparam=i2s=on" /boot/config.txt || \
  echo "dtparam=i2s=on" >> /boot/config.txt

