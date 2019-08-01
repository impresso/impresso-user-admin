import requests
from django.conf import settings

def find_all(q='*:*', fl=settings.IMPRESSO_SOLR_ID_FIELD,
    skip=0,
    limit=settings.IMPRESSO_SOLR_EXEC_LIMIT,
    url=settings.IMPRESSO_SOLR_URL_SELECT,
    auth=settings.IMPRESSO_SOLR_AUTH):
    res = requests.post(url, auth=auth, data={
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

def find_collections_by_ids(ids):
    res = find_all(
        q=' OR '.join(map(lambda id: 'id:%s' % id, ids)),
        fl='id,ucoll_ss,_version_',
        limit=len(ids))
    return res.get('response').get('docs')
