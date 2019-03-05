import json, requests
from django.db import models
from django.contrib.auth.models import User
from . import Bucket
from django.conf import settings

def get_indexed_items(items_ids=[]):
    res = requests.get(settings.IMPRESSO_SOLR_URL_SELECT,
        auth = settings.IMPRESSO_SOLR_AUTH,
        params = {
            'q': ' OR '.join(map(lambda id: 'id:%s' % id, items_ids)),
            'fl': 'id,ucoll_ss,_version_',
            'rows': len(items_ids),
            'wt': 'json',
        }
    )

    res.raise_for_status()
    return res.json().get('response').get('docs')


class Collection(Bucket):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    PRIVATE = 'PRI'
    SHARED = 'PRI'
    PUBLIC = 'PUB'
    DELETED = 'DEL'

    STATUS_CHOICES = (
        (PRIVATE, 'Private'),
        (SHARED, 'Publicly available - only with a link'),
        (PUBLIC, 'Public and indexed'),
        (DELETED, 'In bin, ready to be deleted. No add items after this change.'),
    )

    status = models.CharField(max_length=3, choices=STATUS_CHOICES)


    def add_items_to_index(self, items_ids=[]):
        # get te desired items from SOLR along with their version
        print('collection %s add_items_to_index requests items ...' % self.pk)
        # check if status is bin exit otherwise
        if self.status == Collection.DELETED:
            return {
                'message': 'collection is in BIN',
                'docs': [],
                'todos': [],
            }

        docs = get_indexed_items(items_ids=items_ids)
        todos = []

        for doc in docs:
            # get list of collection in ucoll_ss field
            ucoll_list = doc.get('ucoll_ss', [])

            # TODO update list of collections for this item
            # remove collection otherwise

            # create the indexable name for current collection
            ucoll = '%s:%s' % (self.creator.profile.uid, self.pk)

            if ucoll not in ucoll_list:
                ucoll_list.append(ucoll)

                todos.append({
                    'id': doc.get('id'),
                    '_version_': doc.get('_version_'),
                    'ucoll_ss': {
                        'set': list(set(ucoll_list))
                    }
                })

        if not todos:
            return {
                'message': 'nothing to do',
                'docs': docs,
                'todos': [],
            }

        res = requests.post(settings.IMPRESSO_SOLR_URL_UPDATE,
            auth = settings.IMPRESSO_SOLR_AUTH_WRITE,
            params = {
                'commit': 'true',
                'versions': 'true',
            },
            data = json.dumps(todos),
            json=True,
            headers = {
                'content-type': 'application/json; charset=UTF-8'
            },
        )
        # 5382743
        res.raise_for_status()
        contents = res.json()
        return {
            'message': contents,
            'docs': docs,
            'todos': todos,
        }

    def remove_items_from_index(self, items_ids=[]):
        # get te desired items from SOLR along with their version
        print('collection %s add_items_to_index requests items ...' % self.pk)
        docs = get_indexed_items(items_ids)
        print(docs);


    class Meta(Bucket.Meta):
        db_table = 'collections'
        verbose_name_plural = 'collections'
