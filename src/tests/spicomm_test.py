import contextlib
import mmap
import os
import unittest

import aiy.vision.proto.protocol_pb2 as pb2

from aiy.vision._spicomm import SPICOMM_DEV
from aiy.vision._spicomm import SPICOMM_IOCTL_TRANSACT
from aiy.vision._spicomm import SPICOMM_IOCTL_TRANSACT_MMAP

from aiy.vision._spicomm import AsyncSpicomm
from aiy.vision._spicomm import SyncSpicomm
from aiy.vision._spicomm import SyncSpicommMmap


@contextlib.contextmanager
def SpicommDev():
    dev = os.open(SPICOMM_DEV, os.O_RDWR)
    try:
        yield dev
    finally:
        os.close(dev)

def num_pages(length):
   return (length + mmap.PAGESIZE - 1) // mmap.PAGESIZE


def get_camera_state(spicomm, timeout=None):
    request = pb2.Request(get_camera_state=pb2.Request.GetCameraState())
    response = pb2.Response()
    response.ParseFromString(spicomm.transact(request.SerializeToString(), timeout))
    return response

def get_invalid(spicomm, size, timeout=None):
    response = pb2.Response()
    response.ParseFromString(spicomm.transact(b'A' * size, timeout))
    return response

class SpicommTestMixin:

    def test_empty_request(self):
        with self.Spicomm() as spicomm:
            with self.assertRaises(OSError):
                spicomm.transact(b'')

    def test_valid_request(self):
        with self.Spicomm() as spicomm:
            response = get_camera_state(spicomm)
            self.assertEqual(pb2.Response.Status.OK, response.status.code)

    def test_valid_request_force_allocate(self):
        with self.Spicomm(default_payload_size=8) as spicomm:
            response = get_camera_state(spicomm)
            self.assertEqual(pb2.Response.Status.OK, response.status.code)

    def test_invalid_request(self):
        with self.Spicomm() as spicomm:
            response = get_invalid(spicomm, 32)
            self.assertEqual(pb2.Response.Status.ERROR, response.status.code)

    def test_invalid_request_timeout(self):
        with self.Spicomm() as spicomm:
            with self.assertRaises(OSError):
                response = get_invalid(spicomm, size=1024 * 1024, timeout=0.001)
                self.assertEqual(pb2.Response.Status.OK, response.status.code)

    def test_invalid_request_force_allocate(self):
        with self.Spicomm(default_payload_size=8) as spicomm:
            response = get_invalid(spicomm, 1024 * 1024)
            self.assertEqual(pb2.Response.Status.ERROR, response.status.code)

    def test_huge_invalid_request(self):
        with self.Spicomm(default_payload_size=8) as spicomm:
            response = get_invalid(spicomm, 10 * 1024 * 1024)
            self.assertEqual(pb2.Response.Status.ERROR, response.status.code)

class AsyncSpicommTest(SpicommTestMixin, unittest.TestCase):
    Spicomm = AsyncSpicomm

class SyncSpicommTest(SpicommTestMixin, unittest.TestCase):
    Spicomm = SyncSpicomm

class SyncSpicommMmapTest(SpicommTestMixin, unittest.TestCase):
    Spicomm = SyncSpicommMmap

    def test_multiple_dev(self):
        with SpicommDev() as dev1, SpicommDev() as dev2:
            with mmap.mmap(dev1, length=63, offset = 5 * mmap.PAGESIZE) as mm1, \
                 mmap.mmap(dev2, length=63, offset = 5 * mmap.PAGESIZE) as mm2:
                self.assertEqual(len(mm1), 63)
                self.assertEqual(len(mm2), 63)

    def test_mappings(self):
        with SpicommDev() as dev:
            with mmap.mmap(dev, length=47, offset=0 * mmap.PAGESIZE) as mm1, \
                 mmap.mmap(dev, length=53, offset=1 * mmap.PAGESIZE) as mm2, \
                 mmap.mmap(dev, length=100 * mmap.PAGESIZE + 1, offset=2 * mmap.PAGESIZE) as mm3:
                self.assertEqual(len(mm1), 47)
                self.assertEqual(len(mm2), 53)
                self.assertEqual(len(mm3), 100 * mmap.PAGESIZE + 1)

    def test_big_mappings(self):
        with SpicommDev() as dev:
            with mmap.mmap(dev, length=7 * 1024 * 1024 + 1, offset=0 * mmap.PAGESIZE) as mm1, \
                 mmap.mmap(dev, length=12 * 1024 * 1024 + 2 ,
                    offset=num_pages(len(mm1)) * mmap.PAGESIZE) as mm2:
                self.assertEqual(len(mm1), 7 * 1024 * 1024 + 1)
                self.assertEqual(len(mm2), 12 * 1024 * 1024 + 2)

    def test_multiple_map_unmap(self):
        with SpicommDev() as dev:
            for i in range(1, 100):
                with mmap.mmap(dev, length=i * 40, offset=50 * mmap.PAGESIZE) as mm:
                    self.assertEqual(len(mm), i * 40)

    def test_zero_length_mapping(self):
        with SpicommDev() as dev:
            with self.assertRaises(OSError):
                with mmap.mmap(dev, length=0, offset=0):
                    pass

    def test_max_mappings(self):
        with SpicommDev() as dev, \
             contextlib.ExitStack() as stack:
            for i in range(8):
                stack.enter_context(mmap.mmap(dev, length=mmap.PAGESIZE, offset=i * mmap.PAGESIZE))

            with self.assertRaises(OSError):
                with mmap.mmap(dev, length=mmap.PAGESIZE, offset=100 * mmap.PAGESIZE):
                    pass

    def test_same_offset_mappings(self):
        with SpicommDev() as dev:
            offset = 5 * mmap.PAGESIZE
            with mmap.mmap(dev, length=47, offset=offset):
                with self.assertRaises(OSError):
                    with mmap.mmap(dev, length=54, offset=offset):
                        pass
                with self.assertRaises(OSError):
                    with mmap.mmap(dev, length=1, offset=offset):
                        pass


    def test_overlapping_mappings(self):
        with SpicommDev() as dev:
            with mmap.mmap(dev, length=47, offset=5 * mmap.PAGESIZE) as mm:
                self.assertEqual(len(mm), 47)

                # Right before with overlap
                with self.assertRaises(OSError):
                    with mmap.mmap(dev, length=mmap.PAGESIZE + 1, offset=4 * mmap.PAGESIZE):
                        pass

                # Right before
                with mmap.mmap(dev, length=mmap.PAGESIZE, offset=4 * mmap.PAGESIZE):
                    pass

                # Right after
                with mmap.mmap(dev, length=mmap.PAGESIZE, offset=(1 + 5) * mmap.PAGESIZE):
                    pass


if __name__ == '__main__':
    unittest.main()
