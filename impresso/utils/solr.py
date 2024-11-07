from django.conf import settings
from .bitmap import check_bitmap_keys_overlap


def mapper_doc_redact_contents(doc: dict, user_bitmap_key: str) -> dict:
    """
    Redacts the content of a document based on its bitmap key (_bm_get_tr_s)
    or its availability and year.

    This function modifies the input document dictionary by redacting its content
    if certain conditions are met. Specifically, it checks the "is_content_available"
    field and the document's year to determine if the content should be redacted.

    Args:
        doc (dict): A dictionary representing the document obtained via the serializer function .
            to be considered valid, tt must contain the key "year".
        user_bitmap_key (str): The user's bitmap key.

    Returns:
        dict: The modified document dictionary with redacted content if applicable.

    Notes:
        - If the document's year is greater than or equal to the maximum allowed year
          defined in settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR, the content is redacted.
    """
    try:
        doc_year = int(doc["year"])
    except KeyError:
        print(doc)
        raise ValueError("Document does not contain a 'year' field.")

    if doc.get("access_right", "") == "OpenPublic":
        doc["is_content_available"] = "Y"
    elif doc.get("_bm_get_tr_s", None) is not None:
        if not check_bitmap_keys_overlap(user_bitmap_key, doc["_bm_get_tr_s"]):
            doc["content"] = "[redacted]"
            doc["excerpt"] = "[redacted]"
            doc["is_content_available"] = "N"
            # doc["is_content_available_notes"] = "not authorized"
        else:
            doc["is_content_available"] = "Y"
    elif doc.get("access_right", "") != "OpenPublic":
        doc["content"] = "[redacted]"
        doc["excerpt"] = "[redacted]"
        doc["is_content_available"] = "N"
        # doc["is_content_available_notes"] = "access restricted"
    elif doc_year >= settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR:
        doc["content"] = "[redacted]"
        doc["is_content_available"] = "N"
        # doc["is_content_available_notes"] = "year restricted"
    return doc


def mapper_doc_remove_private_collections(doc: dict, prefix: str) -> dict:
    """
    Removes the private collections from the document that do not start with the job creator's ID.

    Args:
        doc (dict): The document dictionary containing collections.
        prefix (str): The prefix of the collections to keep, actually containing the creator's profile information.

    Returns:
        dict: The updated document dictionary with filtered collections.
    """
    if "collections" in doc:
        # remove collection from the doc if they do not start wirh job creator id
        collections = [d for d in doc["collections"].split(",") if d.startswith(prefix)]
        doc["collections"] = ",".join(collections)
    return doc
