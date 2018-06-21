#!/usr/bin/env python3
import base64
import ctypes
import os
import sys

CRYPTO_ADDRESS_DICT = {
    'Vision Bonnet': 0x60,
    'Voice Bonnet': 0x62,
}


class AtcaIfaceCfgLong(ctypes.Structure):
    _fields_ = (
        ('iface_type', ctypes.c_ulong),
        ('devtype', ctypes.c_ulong),
        ('slave_address', ctypes.c_ubyte),
        ('bus', ctypes.c_ubyte),
        ('baud', ctypes.c_ulong)
    )


def main():
    try:
        name = os.path.join(os.path.dirname(__file__), 'libcryptoauth.so')
        cryptolib = ctypes.cdll.LoadLibrary(name)
    except Exception:
        print('Unable to load crypto library, SW authentication required')
        sys.exit()

    try:
        for name, addr in CRYPTO_ADDRESS_DICT.items():
            cfg = AtcaIfaceCfgLong.in_dll(cryptolib, 'cfg_ateccx08a_i2c_default')
            cfg.slave_address = addr << 1
            cfg.bus = 1  # ARM I2C
            cfg.devtype = 3  # ECC608
            status = cryptolib.atcab_init(cryptolib.cfg_ateccx08a_i2c_default)
            if status == 0:
                # Found a valid crypto chip.
                break
            else:
                cryptolib.atcab_release()

        if status:
            raise Exception

        serial = ctypes.create_string_buffer(9)
        status = cryptolib.atcab_read_serial_number(ctypes.byref(serial))
        if status:
            raise Exception

        serial = ''.join('%02X' % x for x in serial.raw)
        print('Serial Number: %s\n' % serial, file=sys.stderr)

        pubkey = ctypes.create_string_buffer(64)
        status = cryptolib.atcab_genkey_base(0, 0, None, ctypes.byref(pubkey))
        if status:
            raise Exception

        public_key = bytearray.fromhex(
            '3059301306072A8648CE3D020106082A8648CE3D03010703420004') + bytes(pubkey.raw)
        public_key = '-----BEGIN PUBLIC KEY-----\n' + \
            base64.b64encode(public_key).decode('ascii') + '\n-----END PUBLIC KEY-----'
        print(public_key)

        status = cryptolib.atcab_release()
        if status:
            raise Exception
    except Exception:
        print('Unable to communicate with crypto, SW authentication required')


if __name__ == '__main__':
    main()
