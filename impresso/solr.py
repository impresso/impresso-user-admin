import requests
import json
from django.conf import settings


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
    return res.json()


def solr_doc_to_article(doc):
    result = {}
    field = settings.IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS

    for k, v in doc.items():
        prop = field.get(k, None)
        if prop is None:
            prop = k
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
