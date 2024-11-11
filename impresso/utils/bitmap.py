from typing import Union


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
