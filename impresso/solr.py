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
