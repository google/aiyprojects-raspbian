import mmap
import os
import unittest
import contextlib

from aiy._drivers._spicomm import SPICOMM_DEV
from aiy._drivers._spicomm import SPICOMM_IOCTL_TRANSACT
from aiy._drivers._spicomm import SPICOMM_IOCTL_TRANSACT_MMAP

@contextlib.contextmanager
def SpicommDev():
    dev = os.open(SPICOMM_DEV, os.O_RDWR)
    try:
        yield dev
    finally:
        os.close(dev)

def num_pages(length):
   return (length + mmap.PAGESIZE - 1) // mmap.PAGESIZE

class SpicommMmapTest(unittest.TestCase):
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
