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

import fcntl
import mmap
import multiprocessing as mp
import os
import signal
import struct
import threading

SPICOMM_DEV = '/dev/vision_spicomm'

SPICOMM_IOCTL_RESET         = 0x00008901
SPICOMM_IOCTL_TRANSACT      = 0xc0108903
SPICOMM_IOCTL_TRANSACT_MMAP = 0xc0108904

HEADER_SIZE = 4 * 4
DEFAULT_PAYLOAD_SIZE = 12 * 1024 * 1024  # 12M

FLAG_ERROR = 1 << 0
FLAG_TIMEOUT = 1 << 1
FLAG_OVERFLOW = 1 << 2

def _get_default_payload_size():
    return int(os.environ.get('VISION_BONNET_SPICOMM_DEFAULT_PAYLOAD_SIZE',
                              DEFAULT_PAYLOAD_SIZE))


class SpicommError(IOError):
    """Base class for all Spicomm errors."""
    pass


class SpicommOverflowError(SpicommError):
    """Transaction buffer too small for response.

    Attributes:
      size: Number of bytes needed for the response.
    """

    def __init__(self, size):
        super().__init__()
        self.size = size


class SpicommTimeoutError(SpicommError):
    """Transaction timed out."""

    def __init__(self, timeout):
        super().__init__()
        self.timeout = timeout


def _read_header(buf):
    """Returns (flags, timeout_ms, buffer_size, payload_size) tuple."""
    return struct.unpack('IIII', buf[0:HEADER_SIZE])


def _read_payload(buf, payload_size):
    """Returns payload bytes."""
    return buf[HEADER_SIZE:HEADER_SIZE + payload_size]


def _write_header(buf, timeout_ms, payload_size):
    """Writes transaction header into buffer."""
    buf[0:HEADER_SIZE] = struct.pack('IIII', 0, timeout_ms, len(buf), payload_size)


def _write_payload(buf, payload):
    """Writes transaction payload into buffer."""
    buf[HEADER_SIZE:HEADER_SIZE + len(payload)] = payload


def _get_timeout_ms(timeout, payload_size):
    """Conservatively assume minimum 5 seconds or 3 seconds per 1MB."""
    if timeout is not None:
        return int(1000 * timeout)

    return int(1000 * max(3 * payload_size / 1024 / 1024, 5))


def _get_exception(flags, timeout_ms, payload_size):
    if flags & FLAG_ERROR:
        if flags & FLAG_TIMEOUT:
            return SpicommTimeoutError(timeout_ms / 1000.0)
        if flags & FLAG_OVERFLOW:
            return SpicommOverflowError(payload_size)
        return SpicommError()
    return None


def _check_flags(flags, timeout_ms, payload_size):
    e = _get_exception(flags, timeout_ms, payload_size)
    if e is not None:
        raise e


def _async_loop(dev, pipe, default_payload_size):
    # Essentially this process can only receive SIGKILL.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    allocated_buf = bytearray(HEADER_SIZE + default_payload_size)
    while True:
        payload_size, timeout = pipe.recv()
        use_allocated_buf = payload_size <= (len(allocated_buf) - HEADER_SIZE)

        if use_allocated_buf:
            buf = allocated_buf
        else:
            buf = bytearray(HEADER_SIZE + payload_size)

        timeout_ms = _get_timeout_ms(timeout, payload_size)

        _write_header(buf, timeout_ms, payload_size)
        pipe.recv_bytes_into(buf, HEADER_SIZE)

        try:
            fcntl.ioctl(dev, SPICOMM_IOCTL_TRANSACT, buf)
            flags, _, _, payload_size = _read_header(buf)
            e = _get_exception(flags, timeout_ms, payload_size)
            if e is not None:
                pipe.send(e)
            else:
                pipe.send(_read_payload(buf, payload_size))
        except Exception as e:
            pipe.send(e)

class AsyncSpicomm:
    """Class for communication with VisionBonnet via kernel driver.

    Driver ioctl() calls are made inside separate process to allow other threads
    from the current process to work smoothly. Otherwise other threads are blocked
    because of global interpreter lock.
    """

    def __init__(self, default_payload_size=None):
        self._dev = os.open(SPICOMM_DEV, os.O_RDWR)
        self._pipe, pipe = mp.Pipe()
        self._lock = threading.Lock()
        ctx = mp.get_context('fork')

        if default_payload_size is None:
            default_payload_size = _get_default_payload_size()

        self._process = ctx.Process(target=_async_loop, daemon=True,
            args=(self._dev, pipe, default_payload_size))
        self._process.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def close(self):
        os.kill(self._process.pid, signal.SIGKILL)
        self._process.join()
        os.close(self._dev)

    def reset(self):
        fcntl.ioctl(self._dev, SPICOMM_IOCTL_RESET)

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

        # Setup temporary SIGINT handler
        with self._lock:
            captured_args = None
            def handler(*args):
                nonlocal captured_args
                captured_args = args
            old_handler = signal.signal(signal.SIGINT, handler)

            # Execute communication transaction without SIGINT interruptions
            self._pipe.send((len(request), timeout))
            self._pipe.send_bytes(request)
            response = self._pipe.recv()

            # Setup old SIGINT handler or call it directly if SIGINT already happened
            signal.signal(signal.SIGINT, old_handler)
            if captured_args:
                old_handler(*captured_args)

            if isinstance(response, Exception):
                raise response
            return response


class SyncSpicommBase:
    def __init__(self):
        self._lock = threading.Lock()
        self._dev = os.open(SPICOMM_DEV, os.O_RDWR)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def close(self):
        os.close(self._dev)

    def reset(self):
        fcntl.ioctl(self._dev, SPICOMM_IOCTL_RESET)

    def transact(self, request, timeout=None):
        with self._lock:
            return self.transact_impl(request, timeout)

    def transact_impl(self, request, timeout):
        raise NotImplementedError


class SyncSpicomm(SyncSpicommBase):
    """Class for communication with VisionBonnet via kernel driver.

    Driver ioctl() calls are made in the same process. All threads in the current
    process are blocked while icotl() is running because of global interpreter lock.
    """

    def __init__(self, default_payload_size=None):
        super().__init__()
        if default_payload_size is None:
            default_payload_size = _get_default_payload_size()
        self._allocated_buf = bytearray(HEADER_SIZE + default_payload_size)

    def transact_impl(self, request, timeout):
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
        payload_size = len(request)
        use_allocated_buf = payload_size <= (len(self._allocated_buf) - HEADER_SIZE)

        if use_allocated_buf:
            buf = self._allocated_buf
        else:
            buf = bytearray(HEADER_SIZE + payload_size)

        timeout_ms = _get_timeout_ms(timeout, payload_size)

        _write_header(buf, timeout_ms, payload_size)
        _write_payload(buf, request)

        fcntl.ioctl(self._dev, SPICOMM_IOCTL_TRANSACT, buf)
        flags, _, _, payload_size = _read_header(buf)
        _check_flags(flags, timeout_ms, payload_size)

        if use_allocated_buf:
            return bytearray(_read_payload(buf, payload_size))

        return _read_payload(buf, payload_size)


def _transact_mmap(dev, mm, offset, request, timeout):
    payload_size = len(request)
    timeout_ms = _get_timeout_ms(timeout, payload_size)
    flags = 0

    mm[0:payload_size] = request

    buf = bytearray(struct.pack('IIII', flags, timeout_ms, offset, payload_size))
    assert(len(buf) == HEADER_SIZE)

    # Buffer size is small (< 1024 bytes), so ioctl call doesn't block other threads.
    fcntl.ioctl(dev, SPICOMM_IOCTL_TRANSACT_MMAP, buf)
    flags, _, _, payload_size = _read_header(buf)
    _check_flags(flags, timeout_ms, payload_size)
    return bytearray(mm[0:payload_size])


class SyncSpicommMmap(SyncSpicommBase):
    """Class for communication with VisionBonnet via kernel driver.

    Driver ioctl() calls are made in the same process. All threads in the current
    process are *not* blocked while icotl() is running.
    """

    def __init__(self, default_payload_size=None):
        super().__init__()
        if default_payload_size is None:
            default_payload_size = _get_default_payload_size()
        self._mm = mmap.mmap(self._dev, length=default_payload_size, offset=0)

    def close(self):
        self._mm.close()
        super().close()

    def transact_impl(self, request, timeout=None):
        if len(request) < len(self._mm):
            # Default buffer
            return _transact_mmap(self._dev, self._mm, 0, request, timeout)

        # Temporary bigger buffer
        offset = (len(self._mm) + (mmap.PAGESIZE - 1)) // mmap.PAGESIZE
        with mmap.mmap(self._dev, length=len(request), offset=mmap.PAGESIZE * offset) as mm:
            return _transact_mmap(self._dev, mm, offset, request, timeout)


# Scicomm class provides the ability to send and receive data as a transaction.
# This means that every call to transact consists of a combined
# send and receive step that's atomic from the calling application's
# point of view. Multiple threads and processes can access the device
# node concurrently using one Spicomm instance per thread.
# Transactions are serialized in the underlying kernel driver.
_spicomm_type = os.environ.get('VISION_BONNET_SPICOMM', None)
_spicomm_types = {'sync': SyncSpicomm,
                  'sync_mmap': SyncSpicommMmap,
                  'async': AsyncSpicomm}
Spicomm = _spicomm_types.get(_spicomm_type, SyncSpicommMmap)
