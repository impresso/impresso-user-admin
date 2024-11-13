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
            str(BitMask64(10)),
            "0000000000000000000000000000000000000000000000000000000000001010",
        )

    def test_is_access_allowed_edge_cases(self):
        accessor_contents_expectedResult = [
            (0b101111, 10, True),
            (0b101111, 0b100000000, False),
        ]
        for accessor, content, expected_result in accessor_contents_expectedResult:
            accessor_bitmask = BitMask64(accessor)
            content_bitmask = BitMask64(content)
            result = is_access_allowed(accessor_bitmask, content_bitmask)
            self.assertEqual(
                result,
                expected_result,
                "accessor: {} content: {} expected_result: {} result: {}".format(
                    accessor, content, expected_result, result
                ),
            )
