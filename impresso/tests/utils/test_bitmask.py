import unittest
from impresso.utils.bitmask import BitMask64, is_access_allowed


def multiple_assert_equal(
    instance: unittest.TestCase,
    accessor_contents_expectedResult: list[tuple[int, int, bool]] = [
        (0b101111, 10, True),
        (0b101111, 0b100000000, False),
        (0b1, 9223372036854775807, True),
    ],
) -> None:
    """
    Perform multiple assertions to check if access is allowed based on bitmask values.

    Args:
        instance (unittest.TestCase): The test case instance used to perform assertions.
        accessor_contents_expectedResult (list[tuple[int, int, bool]]):
            A list of tuples where each tuple contains:
            - accessor (int): The bitmask value representing the accessor.
            - content (int): The bitmask value representing the content.
            - expected_result (bool): The expected result of the access check.

    Returns:
        None: This function does not return a value. It performs assertions using the provided test case instance.

    Raises:
        AssertionError: If the actual result of the access check does not match the expected result.
    """
    for accessor, content, expected_result in accessor_contents_expectedResult:
        accessor_bitmask = BitMask64(accessor)
        content_bitmask = BitMask64(content)
        result = is_access_allowed(accessor_bitmask, content_bitmask)
        instance.assertEqual(
            result,
            expected_result,
            "\n - accessor: {} \n   {} \n - content: {} \n   {} \n - expected_result: {} \n - result: {}".format(
                accessor,
                str(accessor_bitmask),
                content,
                str(content_bitmask),
                expected_result,
                result,
            ),
        )


class TestBitMask64(unittest.TestCase):
    def test_with_reverse(self):
        self.assertEqual(
            str(BitMask64("111101", reverse=True)),
            "0000000000000000000000000000000000000000000000000000000000101111",
        )
        self.assertEqual(
            str(BitMask64("10", reverse=True)),
            "0000000000000000000000000000000000000000000000000000000000000001",
        )

    def test_init_with_string(self):
        multiple_assert_equal(
            self,
            accessor_contents_expectedResult=[
                (
                    "111101",
                    "0000000000000000000000000000000000000000000000000000000000111101",
                    True,
                ),
                (
                    "010",
                    "0000000000000000000000000000000000000000000000000000000000000010",
                    True,
                ),
            ],
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
        multiple_assert_equal(
            self,
            accessor_contents_expectedResult=[
                (0b101111, 10, True),
                (0b101111, 0b100000000, False),
                (0b1, 9223372036854775807, True),
                (181, 0b10000000, True),
            ],
        )
