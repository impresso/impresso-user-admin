import requests
from django.conf import settings

def find_all(q='*:*', fl=settings.IMPRESSO_SOLR_ID_FIELD,
    skip=0,
    limit=settings.IMPRESSO_SOLR_EXEC_LIMIT,
    url=settings.IMPRESSO_SOLR_URL_SELECT,
    auth=settings.IMPRESSO_SOLR_AUTH):
    res = requests.get(url, auth=auth, params={
        'q': q,
        'fl': fl,
        'start': skip,
        'rows': limit,
        'wt': 'json',
    })
    res.raise_for_status()
    return res.json()

def solr_doc_to_article(doc):
    result = {}
    field = settings.IMPRESSO_SOLR_FIELDS_TO_ARTICLE_PROPS

    for k,v in doc.items():
        prop = field.get(k, None)
        if prop is None:
            prop = k
        if isinstance(v, list):
            result[prop] = ','.join(str(x) for x in v)
        elif not result.get(prop, ''):
            result[prop] = v

    return result
