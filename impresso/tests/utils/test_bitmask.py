import unittest
from impresso.utils.bitmask import BitMask64, is_access_allowed


class TestBitMask64(unittest.TestCase):

    def test_init_with_string(self):
        self.assertEqual(
            str(BitMask64("111101")),
            "0000000000000000000000000000000000000000000000000000000000111101",
        )
        self.assertEqual(
            str(BitMask64("111101", reverse=True)),
            "0000000000000000000000000000000000000000000000000000000000101111",
        )
        self.assertEqual(
            str(BitMask64("10", reverse=True)),
            "0000000000000000000000000000000000000000000000000000000000000001",
        )
        self.assertEqual(
            str(BitMask64("010")),
            "0000000000000000000000000000000000000000000000000000000000000010",
        )

    def test_init_with_int(self):
        self.assertEqual(
            str(BitMask64(0b101111)),
            "0000000000000000000000000000000000000000000000000000000000101111",
        )
        self.assertEqual(
            str(BitMask64(0b101111, reverse=True)),
            "0000000000000000000000000000000000000000000000000000000000101111",
        )
        self.assertEqual(
            str(BitMask64(10)),
            "0000000000000000000000000000000000000000000000000000000000001010",
        )

    def test_is_access_allowed_edge_cases(self):
        accessor_contents_expectedResult = [
            (0b101111, 10, True),
        ]
        for accessor, content, expected_result in accessor_contents_expectedResult:
            accessor_bitmask = BitMask64(accessor, reverse=True)
            content_bitmask = BitMask64(content, reverse=True)
            result = is_access_allowed(accessor_bitmask, content_bitmask)

            print("\nacccessor:\n", str(accessor_bitmask))
            print("content:\n", str(content_bitmask))
            print("is_access_allowed:", result)

            self.assertEqual(
                result,
                expected_result,
                "accessor: {} content: {} expected_result: {} result: {}".format(
                    accessor, content, expected_result, result
                ),
            )

    def test_is_access_allowed_known_cases(self):
        self.assertTrue(
            is_access_allowed(BitMask64("10000"), BitMask64("1")),
            "Content is available, even if the user is not authentified: the content item is available in public domain",
        )

        self.assertFalse(
            is_access_allowed(BitMask64("10000"), BitMask64("10", reverse=True)),
            "Content is not available: the user is not authentified, the content item is available only to authentified users",
        )

        self.assertTrue(
            is_access_allowed(BitMask64("11000"), BitMask64("01", reverse=True)),
            "Content is available: the user is authentified, the content item is available only to authentified users",
        )
