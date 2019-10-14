import json, requests
from django.db import models
from django.contrib.auth.models import User
from . import Bucket
from django.conf import settings

def get_indexed_items(items_ids=[]):
    res = requests.post(settings.IMPRESSO_SOLR_URL_SELECT,
        auth = settings.IMPRESSO_SOLR_AUTH,
        data = {
            'q': ' OR '.join(map(lambda id: 'id:%s' % id, items_ids)),
            'fl': 'id,ucoll_ss,_version_',
            'rows': len(items_ids),
            'wt': 'json',
        }
    )

    res.raise_for_status()
    return res.json().get('response').get('docs')

def set_indexed_items(todos):
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
    return res.json()


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

    def add_items_to_index(self, items_ids=[], logger=None):
        # get te desired items from SOLR along with their version
        # check if status is bin exit otherwise
        if self.status == Collection.DELETED:
            print('collection %s add_items_to_index failed, collection has been deleted ...' % self.pk)

            return {
                'message': 'collection is in BIN',
                'docs': [],
                'todos': [],
            }
        if logger:
            logger.info('Collection pk:{} add_items_to_index - change {} items'.format(
                self.pk,
                len(items_ids),
            ))

        docs = get_indexed_items(items_ids=items_ids)
        todos = []

        for doc in docs:
            # get list of collection in ucoll_ss field
            ucoll_list = doc.get('ucoll_ss', [])
            # create the indexable name for current collection
            ucoll = self.pk

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
            if logger:
                logger.info('Collection {} add_items_to_index nothing to do :)'.format(self.pk))
            return

        contents = set_indexed_items(todos=todos)
        if logger:
            logger.info('Collection {} add_items_to_index SUCCESS for {} items ({} docs updated)!'.format(
                self.pk,
                len(items_ids),
                len(todos),
            ))

        print(contents);


    def remove_items_from_index(self, items_ids=[], logger=None):
        '''
        Remove selected items_ids from this collection
        '''
        if not items_ids:
            if logger:
                logger.info('Collection {} remove_items_from_index, for {} items ..., nothing to do'.format(self.pk, len(items_ids)))
            return
        # get te desired items from SOLR along with their version
        if logger:
            logger.info('Collection {} remove_items_from_index for {} items ...'.format(self.pk, len(items_ids)))
        docs = get_indexed_items(items_ids)
        todos = []
        for doc in docs:
            # get list of collection in ucoll_ss field
            ucoll_list = set(doc.get('ucoll_ss', []))
            # create the indexable name for current collection
            ucoll = self.pk
            if ucoll not in ucoll_list:
                # print('Collection {} not in ucoll_list for id {}, skip.'.format(self.pk, doc.get('id')))
                continue
            ucoll_list.remove(ucoll)

            todos.append({
                'id': doc.get('id'),
                '_version_': doc.get('_version_'),
                'ucoll_ss': {
                    'set': list(ucoll_list)
                }
            })
        if not todos:
            if logger:
                logger.info('Collection {} remove_items_from_index nothing to do :)'.format(self.pk))
            return

        contents = set_indexed_items(todos=todos)
        if logger:
            logger.info('Collection {} remove_items_from_index SUCCESS for {} items ({} docs updated)!'.format(
                self.pk,
                len(items_ids),
                len(todos),
            ))

        print(contents);


    class Meta(Bucket.Meta):
        db_table = 'collections'
        verbose_name_plural = 'collections'
