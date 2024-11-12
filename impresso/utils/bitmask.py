class BitMask64:
    def __init__(self, value: str | int | bytes = 0, reverse: bool = False):
        if isinstance(value, str):
            if not all(c in "01" for c in value):
                raise ValueError("String must contain only '0' and '1'")
            if len(value) > 64:
                raise ValueError("String must contain maximum 64 characters")
            self._value = int(value[::-1], 2) if reverse else int(value, 2)
        elif isinstance(value, int):
            self._value = value
        elif isinstance(value, bytes):
            if len(value) > 8:
                raise ValueError("Bytes must contain maximum 8 bytes")
            self._value = int.from_bytes(value, byteorder="big")
            # // reverse the bits
            self._value = int(bin(self._value)[2:].zfill(64)[::-1], 2)

        else:
            raise TypeError("Value must be a string of bits or an integer.")
        # Ensure the value is within the 64-bit range and pad if necessary
        self._value &= 0xFFFFFFFFFFFFFFFF

    def __int__(self):
        return self._value

    def __str__(self):
        return bin(self._value)[2:].zfill(64)
