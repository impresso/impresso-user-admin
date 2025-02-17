from typing import Union


def is_access_allowed(
    user_permissions_mask: bytes,
    content_permissions_mask: bytes,
) -> bool:
    """
    Checks if the user has access to the content based on the permissions masks.

    Args:
    - content_permissions_mask (bytes): The content permissions mask.
    - user_permissions_mask (bytes): The user permissions mask.

    Returns:
    - bool: Returns True if the user has access to the content, otherwise False.

    Example Usage:
    >>> content_permissions_mask = b"\x01"
    >>> user_permissions_mask = b"\x01"
    >>> is_access_allowed(content_permissions_mask, user_permissions_mask)
    True
    """
    max_len = max(len(user_permissions_mask), len(content_permissions_mask))
    user_mask_padded = user_permissions_mask.rjust(max_len, b"\x00")
    content_mask_padded = content_permissions_mask.rjust(max_len, b"\x00")
    print(f"user_mask_padded: {str(user_mask_padded)}")
    print(f"content_mask_padded: {str(content_mask_padded)}")
    # Perform bitwise AND on each byte pair to check for overlap
    for user_byte, content_byte in zip(user_mask_padded, content_mask_padded):
        if user_byte & content_byte:
            return True  # Found an overlapping permission

    return False  # No overlap found


def int_to_bytes(n: int) -> bytes:
    """
    Converts an integer to a bytes object.

    Args:
    - n (int): The integer to be converted.

    Returns:
    - bytes: The bytes object.

    Example Usage:
    >>> n = 1
    >>> int_to_bytes(n)
    b"\x01"
    """
    return n.to_bytes((n.bit_length() + 7) // 8, "big")


def check_bitmap_keys_overlap(
    user_bitmap_key: str, content_bitmap_key: Union[int, str]
) -> bool:
    """
    Checks if there is any overlap between the user bitmap key and content bitmap key, which can be either
    strings composed of 0 and 1 or integers. The keys are mirrored and only then transformed to integers to perform the
    bitwise AND operation that finally checks if the two keys are compatible.

    Args:
    - user_bitmap_key (str): The str representation of the user bitmap as 0 and 1 only.
    - content_bitmap_key (str or int): The str representation of the content bitmap as 0 and 1 only, or an integer.

    Returns:
    - bool: Returns True if there is any overlap (i.e., if the bitwise AND result has any `1` bits), otherwise False.

    Example Usage:
    >>> user_bitmap_key = "100100"
    >>> content_bitmap_key = "01000000000000"
    >>> check_bitmap_keys_overlap(user_bitmap_key, content_bitmap_key)
    False

    >>> user_bitmap_key = "100100"
    >>> content_bitmap_key = 8192  # equivalent to "01000000000000"
    >>> check_bitmap_keys_overlap(user_bitmap_key, content_bitmap_key)
    False
    """
    try:
        if isinstance(content_bitmap_key, int):
            content_bitmap_long_int = content_bitmap_key
        elif isinstance(content_bitmap_key, str):
            reversed_content_bitmap_key = content_bitmap_key[::-1]
            content_bitmap_long_int = int(reversed_content_bitmap_key, 2)
        else:
            raise ValueError(
                "content_bitmap_key must be either a string of 0 and 1 or an integer"
            )
    except ValueError as e:
        print(
            f"content_bitmap_key must be either a string of 0 and 1 or an integer. Received: {content_bitmap_key}"
        )
        print(f"Error: {e}")
        return False
    try:
        reversed_user_bitmap_key = user_bitmap_key[::-1]
        user_bitmap_long_int = int(reversed_user_bitmap_key, 2)

    except ValueError as e:
        print(
            f"user_bitmap_key and content_bitmap_key must be strings of 0 and 1 only, or content_bitmap_key can be an integer. Received: user_bitmap_key={user_bitmap_key} and content_bitmap_key={content_bitmap_key}"
        )
        print(f"Error: {e}")
        return False
    # Perform the bitwise AND to check if there's any overlap
    # print(f"user_bitmap_long_int: {bin(user_bitmap_long_int)}")
    # print(f"content_bitmap_long_int: {bin(content_bitmap_long_int)}")
    result = user_bitmap_long_int & content_bitmap_long_int
    # print(f"result: {bin(result)} {result > 0}")
    return result > 0
