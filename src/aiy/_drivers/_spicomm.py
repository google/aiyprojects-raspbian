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
"""Python wrapper around the VisionBonnet Spicomm device node."""

import array
import fcntl
import multiprocessing as mp
import os
import struct
import sys


SPICOMM_DEV = '/dev/vision_spicomm'

SPICOMM_IOCTL_BASE = 0x8900
# TODO: 0xc0100000 should be calculated properly base on structure size.
SPICOMM_IOCTL_TRANSACT = 0xc0100000 + SPICOMM_IOCTL_BASE + 3

HEADER_SIZE = 16
DEFAULT_PAYLOAD_SIZE = 12 * 1024 * 1024  # 12 M

FLAG_ERROR = 1 << 0
FLAG_TIMEOUT = 1 << 1
FLAG_OVERFLOW = 1 << 2


class SpicommError(IOError):
    """Base class for all Spicomm errors."""
    pass


class SpicommDevNotFoundError(SpicommError):
    """A usable Spicomm device node not found."""
    pass


class SpicommOverflowError(SpicommError):
    """Transaction buffer too small for response.

    Attributes:
      size: Number of bytes needed for the response.
    """

    def __init__(self, size):
        self.size = size


class SpicommTimeoutError(SpicommError):
    """Transaction timed out."""

    def __init__(self, timeout):
        self.timeout = timeout


def _read_header(buf):
    """Returns (flags, timeout_ms, buffer_size, payload_size) tuple."""
    return struct.unpack('IIII', buf[0:HEADER_SIZE])


def _read_payload(buf):
    """Returns payload bytes."""
    _, _, _, payload_size = _read_header(buf)
    return buf[HEADER_SIZE:HEADER_SIZE + payload_size]


def _write_header(buf, timeout, payload_size):
    """Writes data into transaction header."""
    buf[0:4] = struct.pack('I', 0)                    # flags (used in response)
    buf[4:8] = struct.pack('I', int(timeout * 1000))  # timeout (ms)
    buf[8:12] = struct.pack('I', len(buf))            # buffer size
    buf[12:16] = struct.pack('I', payload_size)       # payload size


def _write_payload(buf, payload):
    buf[HEADER_SIZE:HEADER_SIZE + len(payload)] = payload


def _get_timeout(payload_size):
    """Conservatively assume min 5 seconds or 3 seconds per 1MB."""
    return max(3 * payload_size / 1024 / 1024, 5)


def _get_exception(header):
    flags, timeout_ms, _, payload_size = _read_header(header)
    if flags & FLAG_ERROR:
        if flags & FLAG_TIMEOUT:
            return SpicommTimeoutError(timeout_ms / 1000.0)
        elif flags & FLAG_OVERFLOW:
            return SpicommOverflowError(payload_size)
    return SpicommError()


def _async_loop(pipe):
    allocated_buf = bytearray(HEADER_SIZE + DEFAULT_PAYLOAD_SIZE)

    try:
        dev = open(SPICOMM_DEV, 'r+b', 0)
        pipe.send(None)
    except (IOError, OSError) as e:
        pipe.send(e)
        return

    while True:
        message = pipe.recv()
        if message is None:
            return

        size, timeout = message
        if size <= DEFAULT_PAYLOAD_SIZE:
            buf = allocated_buf
        else:
            buf = bytearray(HEADER_SIZE + size)

        if timeout is None:
            timeout = _get_timeout(size)

        _write_header(buf, timeout, size)
        pipe.recv_bytes_into(buf, HEADER_SIZE)

        try:
            fcntl.ioctl(dev, SPICOMM_IOCTL_TRANSACT, buf)
            pipe.send(_read_payload(buf))
        except (IOError, OSError) as e:
            pipe.send(_get_exception(buf))


class AsyncSpicomm(object):
    """Class for communication with VisionBonnet via kernel driver.

    Driver ioctl() calls are made inside separate process to allow other threads
    from the current process to work smoothly. Otherwise other threads are blocked
    because of global interpreter lock.
    """

    def __init__(self):
        ctx = mp.get_context('fork')
        self._pipe, pipe = mp.Pipe()
        self._process = ctx.Process(target=_async_loop, daemon=True, args=(pipe,))
        self._process.start()

        status = self._pipe.recv()
        if isinstance(status, Exception):
            raise status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def close(self):
        self._pipe.send(None)
        self._process.join()

    def transact(self, request, timeout=None):
        """Execute transaction in a separate process.

        Args:
          request: Request bytes to send.
          timeout: How long a response will be waited for, in seconds.

        Returns:
          Bytes-like object with response data.

        Raises:
          SpicommOverflowError: Transaction buffer was too small for response.
          SpicommTimeoutError: Transaction timed out.
          SpicommError: Transaction error.
        """
        self._pipe.send((len(request), timeout))
        self._pipe.send_bytes(request)
        response = self._pipe.recv()
        if isinstance(response, Exception):
            raise response
        return response


class SyncSpicomm(object):
    """Class for communication with VisionBonnet via kernel driver.

    Driver ioctl() calls are made in the same process. All threads in the current
    process are blocked while icotl() is running because of global interpreter lock.
    """

    def __init__(self):
        try:
            self._dev = open(SPICOMM_DEV, 'r+b', 0)
        except (IOError, OSError):
            raise SpicommDevNotFoundError
        self._allocated_buf = bytearray(HEADER_SIZE + DEFAULT_PAYLOAD_SIZE)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def close(self):
        self._dev.close()

    def transact(self, request, timeout=None):
        """Execute transaction in the current process.

        Args:
          request: Request bytes to send.
          timeout: How long a response will be waited for, in seconds.

        Returns:
          Bytes-like object with response data.

        Raises:
          SpicommOverflowError: Transaction buffer was too small for response.
          SpicommTimeoutError: Transaction timed out.
          SpicommError: Transaction error.
        """
        size = len(request)
        if size <= DEFAULT_PAYLOAD_SIZE:
            buf = self._allocated_buf
        else:
            buf = bytearray(HEADER_SIZE + size)

        if timeout is None:
            timeout = _get_timeout(size)

        _write_header(buf, timeout, size)
        _write_payload(buf, request)

        try:
            fcntl.ioctl(self._dev, SPICOMM_IOCTL_TRANSACT, buf)
            return _read_payload(buf)
        except (IOError, OSError):
            raise _get_exception(buf)


_spicomm_type = os.environ.get('VISION_BONNET_SPICOMM', None)
_spicomm_types = {'sync': SyncSpicomm, 'async': AsyncSpicomm}

# Scicomm class provides the ability to send and receive data as a transaction.
# This means that every call to transact consists of a combined
# send and receive step that's atomic from the calling application's
# point of view. Multiple threads and processes can access the device
# node concurrently using one Spicomm instance per thread.
# Transactions are serialized in the underlying kernel driver.
Spicomm = _spicomm_types.get(_spicomm_type, AsyncSpicomm)
