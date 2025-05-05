import requests
import json
import logging
from django.conf import settings
from typing import Dict, Any, Optional, List


def find_all(
    q: str = "*:*",
    fl: str = settings.IMPRESSO_SOLR_FL_ID,
    skip: int = 0,
    limit: int = settings.IMPRESSO_SOLR_EXEC_LIMIT,
    url: str = settings.IMPRESSO_SOLR_URL_SELECT,
    auth: tuple = settings.IMPRESSO_SOLR_AUTH,
    logger: Optional[logging.Logger] = None,
    sort: str = "id ASC",
    fq: str = "",
) -> Dict[str, Any]:
    """
    Execute a query against a Solr instance and return the results.

    Args:
        q (str): The query string. Defaults to "*:*".
        fl (str): The fields to return. Defaults to settings.IMPRESSO_SOLR_FL_ID.
        skip (int): The number of records to skip. Defaults to 0.
        limit (int): The maximum number of records to return. Defaults to settings.IMPRESSO_SOLR_EXEC_LIMIT.
        url (str): The Solr URL to send the request to. Defaults to settings.IMPRESSO_SOLR_URL_SELECT.
        auth (tuple): Authentication credentials for Solr. Defaults to settings.IMPRESSO_SOLR_AUTH.
        logger (Optional[logging.Logger]): Logger instance for logging. Defaults to None.
        sort (str): The sort order of the results. Defaults to "id ASC".
        fq (str): The filter query. Defaults to an empty string.

    Returns:
        dict: The response from the Solr instance as a dictionary.

    Raises:
        requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
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
    data = res.json()
    return data


def find_collections_by_ids(ids: List[str]) -> List[Dict[str, Any]]:
    res = find_all(
        q=" OR ".join(map(lambda id: "id:%s" % id, ids)),
        fl="id,ucoll_ss,_version_",
        limit=len(ids),
    )
    return res.get("response", {}).get("docs", [])


def update(
    todos: List[Dict[str, Any]],
    url: Optional[str] = None,
    auth: tuple = settings.IMPRESSO_SOLR_AUTH,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
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
