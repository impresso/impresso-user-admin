def check_bitmap_keys_overlap(user_bitmap_key: str, content_bitmap_key: str) -> bool:
    """
    Checks if there is any overlap between the user bitmap key and content bitmap key, basically
    strings composed of 0 and 1. The keys are mirrored and only then transformed to integers to perform the
    bitwise AND operation that finally check if the two keys are compatible.

    Args:
    - user_bitmap (str): The str representation of the user bitmap as 0 and 1 only.
    - content_bitmap (str): The str representation of the content bitmap as 0 and 1 only.

    Returns:
    - int: Returns 1 if there is any overlap (i.e., if the bitwise AND result has any `1` bits), otherwise 0.

    Example Usage:
    >>> user_bitmap_key = "100100"
    >>> content_bitmap_key = "01000000000000"
    >>> check_bitmaps_overlap(user_bitmap_key, content_bitmap_key)
    0
    """
    reversed_user_bitmap_key = user_bitmap_key[::-1]
    reversed_content_bitmap_key = content_bitmap_key[::-1]
    # transform to int
    user_bitmap = int(reversed_user_bitmap_key, 2)
    content_bitmap = int(reversed_content_bitmap_key, 2)

    # print(f"user reversed original:\n {user_bitmap:05b}")
    # print(f"content reversed original:\n {content_bitmap:05b}")
    # Perform the bitwise AND to check if there's any overlap
    result = user_bitmap & content_bitmap
    # print(f"result:\n {result:05b}")
    return result > 0
