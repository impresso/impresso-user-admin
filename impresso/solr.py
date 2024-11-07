import requests
import json
from django.conf import settings
from typing import Dict, Any
import re


class JsonWithBitmapDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        # Override raw_decode to handle custom preprocessing
        self.original_raw_decode = self.raw_decode
        self.raw_decode = self.custom_raw_decode
        super().__init__(*args, **kwargs)

    def custom_raw_decode(self, s, idx=0):
        # Replace binary literals in the JSON string
        processed_string = re.sub(r":\s*0b[01]+", self._binary_to_decimal, s)
        # Decode the processed string with the original method
        return self.original_raw_decode(processed_string, idx)

    def _binary_to_decimal(self, match):
        # Extract the binary string (strip leading ': ' characters) and convert it
        binary_str = match.group(0).split("0b")[-1]  # Isolate '0bxxxx'
        # important invert the string
        binary_str_flipped = binary_str[::-1]
        return f': "{binary_str_flipped}"'


def parse_dpsf_field(dpsf_string: str) -> list:
    """Parses a DPSF field string into a list of dictionaries.

    Args:
      dpsf_string: The DPSF field string.

    Returns:
      A list of dictionaries, where each dictionary represents a key-value pair.
    """

    # Split the string into individual key-value pairs
    pairs = dpsf_string.split(" ")

    # Create a list of dictionaries
    result = []
    for pair in pairs:
        key, value = pair.split("|")
        result.append({"key": key, "value": float(value)})

    return result


def find_all(
    q="*:*",
    fl=settings.IMPRESSO_SOLR_ID_FIELD,
    skip=0,
    limit=settings.IMPRESSO_SOLR_EXEC_LIMIT,
    url=settings.IMPRESSO_SOLR_URL_SELECT,
    auth=settings.IMPRESSO_SOLR_AUTH,
    logger=None,
    sort="id ASC",
    fq="",  # {!collapse field=ISBN}
):
    if logger:
        logger.info("query:{} skip:{}".format(q, skip))

    data = {"q": q, "fq": fq} if fq else {"q": q}

    params = {
        "fl": fl,
        "start": int(skip),
        "rows": int(limit),
        "wt": "json",
        "hl": "off",
        "sort": sort,
    }

    res = requests.post(url, auth=auth, params=params, data=data)
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if logger:
            logger.info(res.text)
            logger.exception(err)
        else:
            print(res.text)
        raise
    data = res.json(cls=JsonWithBitmapDecoder)
    return data


def solr_doc_to_content_item(
    doc: Dict[str, Any],
    field_mapping: Dict[str, str] = settings.IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS,
) -> Dict[str, str]:
    """
    Convert a Solr document to a content item object as adict

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


def find_collections_by_ids(ids):
    res = find_all(
        q=" OR ".join(map(lambda id: "id:%s" % id, ids)),
        fl="id,ucoll_ss,_version_",
        limit=len(ids),
    )
    return res.get("response").get("docs")


def update(todos, url=None, auth=settings.IMPRESSO_SOLR_AUTH, logger=None):
    if logger:
        logger.info(f"todos n:{len(todos)} for url:{url}")
    res = requests.post(
        url,
        auth=settings.IMPRESSO_SOLR_AUTH_WRITE,
        params={"commit": "true", "versions": "true", "fl": "id"},
        data=json.dumps(todos),
        json=True,
        headers={"content-type": "application/json; charset=UTF-8"},
    )
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if logger:
            logger.info("sending data: {}".format(json.dumps(todos)))
            logger.info(res.text)
            logger.exception(err)
        raise
    return res.json()
