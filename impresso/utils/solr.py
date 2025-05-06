from typing import Dict, Any
from django.conf import settings
from .bitmask import is_access_allowed, BitMask64


def serialize_solr_doc_content_item_to_plain_dict(
    doc: Dict[str, Any],
    field_mapping: Dict[str, str] = settings.IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS,
) -> Dict[str, str]:
    """
    Convert a Solr document to a content item object as a dictionary.

    Args:
        doc: Solr document
        field_mapping: Mapping between Solr fields and content item properties

    Returns:
        dict: Content item object
    """
    result: Dict[str, str] = {}

    for k, v in doc.items():
        prop = field_mapping.get(k, None)
        if prop is None:
            continue
        if isinstance(v, list):
            result[prop] = ",".join(str(x) for x in v)
        elif not result.get(prop, ""):
            result[prop] = v

    return result


def mapper_doc_redact_contents(doc: dict, user_bitmask: BitMask64) -> dict:
    """
    Redacts the content of a document based on its bitmap key (_bm_get_tr_s)
    or its availability and year.

    This function modifies the input document dictionary by redacting its content
    if certain conditions are met. Specifically, it checks the "is_content_available"
    field and the document's year to determine if the content should be redacted.

    Args:
        doc (dict): A dictionary representing the document obtained via the serializer function .
            to be considered valid, tt must contain the key "year".
        user_bitmask (BitMask64): The user's bitmap key, as BitMask64 instance.

    Returns:
        dict: The modified document dictionary with redacted content if applicable.

    Notes:
        - If the document's year is greater than or equal to the maximum allowed year
          defined in settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR, the content is redacted.
    """
    try:
        doc_year = int(doc[settings.IMPRESSO_SOLR_FL_YEAR_LABEL])
    except KeyError:
        print(doc)
        raise ValueError("Document does not contain a 'year' field.")

    is_transcript_available = False
    content_bitmask = doc.get(f"_{settings.IMPRESSO_SOLR_FL_TRANSCRIPT_BM}", None)
    if content_bitmask is not None:
        is_transcript_available = is_access_allowed(
            accessor=user_bitmask,
            content=BitMask64(content_bitmask),
        )
    # Previous check
    # if doc.get("_bm_get_tr_i", None) is not None:
    #     is_transcript_available = is_access_allowed(
    #         accessor=user_bitmask,
    #         content=BitMask64(doc["_bm_get_tr_i"], reverse=True),
    #     )
    # elif doc.get("_bm_get_tr_s", None) is not None:
    #     is_transcript_available = is_access_allowed(
    #         accessor=user_bitmask,
    #         # nop need to reverse if this is a string
    #         content=BitMask64(doc["_bm_get_tr_s"]),
    #     )
    # elif doc.get("access_right", "") == "OpenPublic":
    #     is_transcript_available = True
    # edge cases
    elif doc_year < settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR:
        is_transcript_available = True
        # doc["is_content_available_notes"] = "year restricted"
    if is_transcript_available:
        doc["is_content_available"] = "Y"
    else:
        doc[settings.IMPRESSO_SOLR_FL_CONTENT_LABEL] = (
            settings.IMPRESSO_CONTENT_REDACTED_LABEL
        )
        doc[settings.IMPRESSO_SOLR_FL_EXCERPT_LABEL] = (
            settings.IMPRESSO_CONTENT_REDACTED_LABEL
        )
        doc["is_content_available"] = "N"

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
