from __future__ import absolute_import

import json, time, math
import requests

from django.core import serializers
from django.conf import settings
from django.db.utils import IntegrityError

from .celery import app
from .models import Job, Collection, CollectableItem


@app.task(bind=True)
def echo(self, message):
    print('Request: {0!r}'.format(self.request))
    print('Message: {0}'.format(message))
    return message


@app.task(bind=True, autoretry_for=(Exception,), exponential_backoff=2, retry_kwargs={'max_retries': 5}, retry_jitter=True)
def store_collectable_items(self, job_id, collection_id, skip=0, limit=10, taskname='store_collectable_items'):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    job.status = Job.RUN

    # get the collection!
    collection = Collection.objects.get(pk=collection_id)

    # get the collection status
    items = CollectableItem.objects.filter(
        collection = collection,
        content_type = CollectableItem.ARTICLE
    )
    total = items.count()
    loops = math.ceil(total / limit)
    page = skip / limit + 1
    progress = page / loops
    taskstate = 'PROGRESS'

    # get the collectableItems ids in the collection
    items_ids = items.values_list('item_id', flat=True)[skip:limit]

    # do the right thing
    collection.add_items_to_index(items_ids=items_ids)

    if page == loops:
        taskstate = 'SUCCESS'
        job.status = Job.DONE
    else:
        # queue job.
        store_collectable_items.delay(
            job_id = job.pk,
            collection_id = collection.pk,
            skip = int(page * limit),
            taskname = taskname
        )

    # update status meta
    meta = {
        'task': taskname,
        'progress': progress,
        'job_id': job.pk,
        'user_id': job.creator.pk,
        'extra': {
            # 'QTime': qtime,
            'total': total,
            # here we put the actual loops needed.
            'loops':  loops,
            'page': page,
            'limit': limit,
            'skip': skip,
        },
        'ids': [id for id in items_ids],
    }

    job.extra = json.dumps(meta)
    job.save()

    # update state
    self.update_state(state = taskstate, meta = meta)

    # return job, to be seen in info
    return serializers.serialize('json', (job,))



@app.task(bind=True)
def store_collection(self, collection_id):
    # get the collection
    collection = Collection.objects.get(pk=collection_id)
    # save current job!
    job = Job.objects.create(
        type=Job.SYNC_COLLECTION_TO_SOLR,
        creator=collection.creator
    );
    # start update chain
    store_collectable_items.delay(
        job_id = job.pk,
        collection_id = collection.pk,
    )

    # if alles gut
    self.update_state(state = "INIT", meta = {
        'task': 'sync_collection_in_solr',
        'progress': 0,
        'job_id': job.pk,
        'user_id': collection.creator.pk,
    })

    return serializers.serialize('json', (job,))


@app.task(bind=True)
def count_items_in_collection(self, collection_id):

    pass

@app.task(bind=True)
def execute_solr_query(self, query, job_id, collection_id, content_type, skip=0):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    # get limit from settings
    limit = settings.IMPRESSO_SOLR_EXEC_LIMIT

    # now execute solr query, along with first `limit` rows
    res = requests.get(settings.IMPRESSO_SOLR_URL_SELECT, auth = settings.IMPRESSO_SOLR_AUTH, params = {
        'q': query,
        'fl': settings.IMPRESSO_SOLR_ID_FIELD,
        'start': skip,
        'rows': limit,
        'wt': 'json',
    })
    # should repeat until this gets None
    res.raise_for_status()

    contents = res.json()
    # print(contents)
    # did something bad happen? report to job

    # calculate remaining loops
    total = contents['response']['numFound']

    qtime = contents['responseHeader']['QTime']
    page = skip / limit + 1
    loops = math.ceil(min(total, settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS) / limit)

    meta = {
        'task': 'execute_solr_query',
        'progress': 0,
        'job_id': job.pk,
        'user_id': job.creator.pk,
        'extra': {
            'QTime': qtime,
            'total': total,
            # here we put the actual loops needed.
            'loops':  loops,
            'realloops': math.ceil(total / limit),
            'maxloops': settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS,
            'page': page,
            'limit': limit,
            'skip': skip,
        },
        'warnings': [],
    }

    # calculate progresses
    if total:
        meta['progress'] = page / loops

    # is the job done?
    if page <= loops:
        job.status = Job.RUN

        # get the collection
        collection = Collection.objects.get(pk=collection_id);

        # add items to the collection!
        try:
            CollectableItem.objects.bulk_create(map(
                lambda item_id: CollectableItem(
                    item_id = item_id,
                    content_type = content_type,
                    collection = collection,
                ),
                [*map(lambda doc: doc.get(settings.IMPRESSO_SOLR_ID_FIELD), contents['response']['docs'])]
            ))
        except IntegrityError as e:
            meta['warnings'].append(str(e))


        # once it's done, go on with the following execution!
        execute_solr_query.delay(
            query = query,
            job_id = job_id,
            collection_id = collection_id,
            content_type = content_type,
            skip = (skip + limit)
        )
    else:
        job.status = Job.DONE


    job.extra = json.dumps(meta)
    job.save()

    # update state
    self.update_state(state = "PROGRESS" if job.status == Job.RUN else "SUCCESS", meta = meta)

    # return job, to be seen in info
    return serializers.serialize('json', (job,))
    # next loop if needed
    # if(loops > 0) {
    #
    # }
    # users = all_users()
    # for u in users:
    # add_to_collection.delay(
    #     collection_id = collection_id,
    #     item_id = item_id,
    #     job_id = job_id,
    #     user_id = job.creator.pk,
    # )

@app.task(bind=True)
def remove_collection(self, collection_id, user_id):
    # check that the collection (still) exists!
    collection = Collection.objects.get(pk=collection_id, creator__id=user_id);

    # save current job!
    job = Job.objects.create(
        type=Job.DELETE_COLLECTION,
        creator=collection.creator
    );

    # remove in bunch of 1000
    remove_from_collection.delay(
        job_id = job.pk,
        collection_id = collection.pk,
    )
    return serializers.serialize('json', (job,))


@app.task(bind=True)
def remove_from_collection(self, job_id, collection_id, user_id):
    pass


@app.task(bind=True)
def add_to_collection_from_query(self, collection_id, user_id, query, content_type):
    # check that the collection exists!
    collection = Collection.objects.get(pk=collection_id, creator__id=user_id);

    # save current query @TODO

    # save current job!
    job = Job.objects.create(
        type=Job.BULK_COLLECTION_FROM_QUERY,
        creator=collection.creator
    );

    # if alles gut
    self.update_state(state = "INIT", meta = {
        'task': 'add_to_collection_from_query',
        'progress': 0,
        'job_id': job.pk,
        'user_id': collection.creator.pk,
    })

    # execute premiminary query
    execute_solr_query.delay(
        query  = query,
        job_id = job.pk,
        collection_id = collection.pk,
        content_type = content_type,
    )

    return serializers.serialize('json', (job,))
