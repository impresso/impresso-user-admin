class BitMask64:
    def __init__(self, value: str | int | bytes = 0, reverse: bool = False):
        if isinstance(value, str):
            if not all(c in "01" for c in value):
                raise ValueError("String must contain only '0' and '1'")
            if len(value) > 64:
                raise ValueError("String must contain maximum 64 characters")
            self._value = int(f"{value:064}"[::-1], 2) if reverse else int(value, 2)
        elif isinstance(value, int):
            self._value = int(f"{value:064b}", 2) if reverse else value
        elif isinstance(value, bytes):
            if len(value) > 8:
                raise ValueError("Bytes must contain maximum 8 bytes")
            self._value = int.from_bytes(value, byteorder="big")
        else:
            raise TypeError(
                "Value must be a string of bits or an integer. Type:", type(value)
            )
        # Ensure the value is within the 64-bit range and pad if necessary
        # self._value &= 0xFFFFFFFFFFFFFFFF

    def __int__(self):
        return self._value

    def __str__(self):
        return bin(self._value)[2:].zfill(64)


def is_access_allowed(accessor: BitMask64, content: BitMask64) -> bool:
    """
    Check if access is allowed based on the provided bit masks.

    This function takes two BitMask64 objects, `accessor` and `content`, and
    performs a bitwise AND operation to determine if access is allowed. If the
    result of the bitwise AND operation is greater than 0, access is allowed.

    Args:
        accessor (BitMask64): The bit mask representing the accessor's permissions.
        content (BitMask64): The bit mask representing the content's required permissions.
                             If an integer is provided, it will be reversed.

    Returns:
        bool: True if access is allowed, False otherwise.
    """
    result = int(accessor) & int(content)
    return result > 0


def int_to_bytes(n: int) -> bytes:
    """
    Convert an integer to a bytes object.

    Args:
        n (int): The integer to convert to bytes.

    Returns:
        bytes: The bytes object representing the integer.
    """
    return n.to_bytes((n.bit_length() + 7) // 8, "big")
