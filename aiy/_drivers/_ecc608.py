# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import base64
import ctypes
import json
import datetime
import logging
import os
import sys
import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)


class AtcaIfaceCfgLong(ctypes.Structure):
    _fields_ = (
        ('iface_type', ctypes.c_ulong),
        ('devtype', ctypes.c_ulong),
        ('slave_address', ctypes.c_ubyte),
        ('bus', ctypes.c_ubyte),
        ('baud', ctypes.c_ulong)
    )


def _ecc608_check_address(address):
    cfg = AtcaIfaceCfgLong.in_dll(_cryptolib, 'cfg_ateccx08a_i2c_default')
    cfg.slave_address = address << 1  # Cryptolib uses 8-bit address.
    cfg.bus = 1  # ARM I2C
    cfg.devtype = 3  # ECC608
    status = _cryptolib.atcab_init(_cryptolib.cfg_ateccx08a_i2c_default)
    if status == 0:
        return True
    _cryptolib.atcab_release()
    return False


def ecc608_find_chip():
    """Returns the I2C address of the crypto chip or None if chip is not installed."""

    for addr in (0x60, 0x62):
        if _ecc608_check_address(addr):
            logger.info('Found crypto chip at 0x%x.', addr)
            return addr
    logger.warning('No crypto detected, using SW.')
    return None

def ecc608_hw_sign(msg):
    digest = ctypes.create_string_buffer(32)
    status = _cryptolib.atcab_sha(len(msg), ctypes.c_char_p(msg), ctypes.byref(digest))
    assert status == 0

    signature = ctypes.create_string_buffer(64)
    status = _cryptolib.atcab_sign(0, ctypes.byref(digest), ctypes.byref(signature))
    assert status == 0
    return signature.raw


def ecc608_man_jwt(claims):
    header = '{"typ":"JWT","alg":"ES256"}'

    for k, v in claims.items():
        if type(v) is datetime.datetime:
            claims[k] = int(v.timestamp())

    payload = json.dumps(claims)

    token = base64.urlsafe_b64encode(
        header.encode('ascii')).replace(b'=', b'') + b'.'

    token = token + \
        base64.urlsafe_b64encode(payload.encode('ascii')).replace(b'=', b'')

    signature = ecc608_hw_sign(token)

    token = token + b'.' + \
        base64.urlsafe_b64encode(signature).replace(b'=', b'')
    return token


def ecc608_serial():
    serial = ctypes.create_string_buffer(9)
    status = _cryptolib.atcab_read_serial_number(ctypes.byref(serial))
    assert status == 0
    return ''.join('%02X' % x for x in serial.raw)


def ecc608_public_key():
    pubkey = ctypes.create_string_buffer(64)
    status = _cryptolib.atcab_genkey_base(0, 0, None, ctypes.byref(pubkey))
    assert status == 0
    return bytes(pubkey.raw)


class HwEcAlgorithm(jwt.algorithms.Algorithm):
    def __init__(self):
        self.hash_alg = hashes.SHA256

    def prepare_key(self, key):
        return key

    def sign(self, msg, key):
        return ecc608_hw_sign(msg)

    def verify(self, msg, key, sig):
        try:
            der_sig = jwt.utils.raw_to_der_signature(sig, key.curve)
        except ValueError:
            return False

        try:
            key.verify(der_sig, msg, ec.ECDSA(self.hash_alg()))
            return True
        except InvalidSignature:
            return False

# On module import, load library.
try:
    ecc608_i2c_address = None
    ecc608_jwt_with_hw_alg = None

    _name = os.path.join(os.path.dirname(__file__), 'libcryptoauth.so')
    _cryptolib = ctypes.cdll.LoadLibrary(_name)

    ecc608_i2c_address = ecc608_find_chip()
    if ecc608_i2c_address is not None:
        ecc608_jwt_with_hw_alg = jwt.PyJWT(algorithms=[])
        ecc608_jwt_with_hw_alg.register_algorithm('ES256', HwEcAlgorithm())
except Exception:
    logger.warning('Unable to load HW crypto library, using SW.')
