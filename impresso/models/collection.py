import json, requests
from django.db import models
from django.contrib.auth.models import User
from . import Bucket
from django.conf import settings


class Collection(Bucket):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    STATUS_CHOICES = (
        ('PRI', 'Private'),
        ('SHA', 'Publicly available - only with a link'),
        ('PUB', 'Public and indexed'),
    )

    status = models.CharField(max_length=3, choices=STATUS_CHOICES)


    def add_items_to_index(self, items_ids=[]):
        # get te desired items from SOLR along with their version
        print('collection %s add_items_to_index requests items ...' % self.pk)

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

        print('collection %s add_items_to_index requests succeed' % self.pk)
        # SOLR documents
        docs = res.json().get('response').get('docs')
        todos = []

        for doc in docs:
            # get list of collection in ucoll_ss field
            ucoll_list = doc.get('ucoll_ss', [])
            ucoll = '%s:%s' % (self.creator.pk, self.pk)

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

    class Meta(Bucket.Meta):
        db_table = 'collections'
        verbose_name_plural = 'collections'
