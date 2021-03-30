#!/bin/bash

set -o xtrace
set -o errexit

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pushd ${SCRIPT_DIR}/vision
dpkg-buildpackage -b -rfakeroot -us -uc -tc
popd

pushd ${SCRIPT_DIR}/voice
dpkg-buildpackage -b -rfakeroot -us -uc -tc
popd
