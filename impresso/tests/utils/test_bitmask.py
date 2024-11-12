import unittest
from impresso.utils.bitmask import BitMask64


class TestBitMask64(unittest.TestCase):

    def test_init_with_string(self):
        bitmask = BitMask64("010110101")
        self.assertEqual(
            str(bitmask),
            "0000000000000000000000000000000000000000000000000000000010110101",
        )

        reverted_bitmask = BitMask64("010110101", reverse=True)
        # we expect 0b101011010 = 346
        self.assertEqual(int(reverted_bitmask), 0b101011010)
