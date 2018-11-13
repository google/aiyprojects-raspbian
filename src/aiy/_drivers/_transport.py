# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Transport to communicate with VisionBonnet board."""

import logging
import os
import socket
import struct

from aiy._drivers import _spicomm


class _SpiTransport:
    """Communicate with VisionBonnet over SPI bus."""

    def __init__(self):
        self._spicomm = _spicomm.Spicomm()

    def send(self, request, timeout=None):
        return self._spicomm.transact(request, timeout=timeout)

    def close(self):
        self._spicomm.close()


def _socket_recvall(s, size):
    buf = b''
    while size:
        newbuf = s.recv(size)
        if not newbuf:
            return None
        buf += newbuf
        size -= len(newbuf)
    return buf


def _socket_receive_message(s):
    buf = _socket_recvall(s, 4)  # 4 bytes
    if not buf:
        return None
    size = struct.unpack('!I', buf)[0]
    return _socket_recvall(s, size)


def _socket_send_message(s, msg):
    s.sendall(struct.pack('!I', len(msg)))  # 4 bytes
    s.sendall(msg)  # len(msg) bytes


class _SocketTransport:
    """Communicate with VisionBonnet over socket."""

    def __init__(self):
        """Open connection to the bonnet."""
        self._client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        host = os.environ.get('VISION_BONNET_HOST', '172.28.28.10')
        port = int(os.environ.get('VISION_BONNET_PORT', '35000'))
        self._client.connect((host, port))

    def send(self, request, timeout=None):
        _socket_send_message(self._client, request)
        return _socket_receive_message(self._client)

    def close(self):
        self._client.close()


def _is_arm():
    return os.uname()[4].startswith('arm')


def make_transport():
    if _is_arm():
        return _SpiTransport()
    return _SocketTransport()
