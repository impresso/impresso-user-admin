from __future__ import absolute_import

import json, time, math, csv
import requests

from django.core import serializers
from django.conf import settings
from django.db.utils import IntegrityError

from .celery import app
from .models import Job, Collection, CollectableItem, SearchQuery, Attachment
from .solr import find_all, solr_doc_to_article

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@app.task(bind=True)
def echo(self, message):
    print('Request: {0!r}'.format(self.request))
    print('Message: {0}'.format(message))
    return message


@app.task(bind=True)
def test_progress(self, job_id, sleep=5, pace=0.1, progress=0.0):
    # do heavy stuff during this time
    if progress > 0:
        time.sleep(sleep)
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    # check if job needs to be stopped
    if job.status == Job.STOP:
         job.status = Job.DONE
         taskstate = 'STOPPED'
         meta = job.get_task_meta(taskname='test', progress=progress, extra={
             'pace': pace,
             'sleep': sleep,
             'stopped': True
         })
         job.extra = json.dumps(meta)
         job.save()
         # update state
         self.update_state(state = taskstate, meta = meta)
         # return job, to be seen in info
         return serializers.serialize('json', (job,))

    if progress < 1.0:
        taskstate = 'PROGRESS'
        job.status = Job.RUN
        # call the same function and
        test_progress.delay(
            job_id=job.pk,
            sleep=sleep,
            pace=pace,
            progress=progress + pace
        )
    else:
        taskstate = 'SUCCESS'
        job.status = Job.DONE
    # update job status and meta
    meta = job.get_task_meta(taskname='test', progress=progress, extra = {
        'pace': pace,
        'sleep': sleep
    })
    job.extra = json.dumps(meta)
    job.save()
    # update state
    self.update_state(state = taskstate, meta = meta)
    # return job, to be seen in info
    return serializers.serialize('json', (job,))


@app.task(bind=True)
def test(self, user_id):
    # save current job then start test_progress task.
    job = Job.objects.create(
        type=Job.TEST,
        creator_id=user_id
    );
    test_progress.delay(job_id=job.pk)
    return serializers.serialize('json', (job,))



@app.task(bind=True, autoretry_for=(Exception,), exponential_backoff=2, retry_kwargs={'max_retries': 5}, retry_jitter=True)
def export_query_as_csv_progress(self, job_id, query, skip=0):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    # check if job needs to be stopped
    if job.status == Job.STOP:
         job.status = Job.DONE
         taskstate = 'STOPPED'
         meta = job.get_task_meta(taskname='export_query_as_csv', progress=progress, extra={
             'stopped': True
         })
         job.extra = json.dumps(meta)
         job.save()
         # update state
         self.update_state(state = taskstate, meta = meta)
         # return job, to be seen in info
         return serializers.serialize('json', (job,))

    # do find_all
    logger.info('  export_query_as_csv, loading query: %s' % query)
    contents = find_all(q=query, fl=settings.IMPRESSO_SOLR_FIELDS, skip=skip)

    # get limit from settings
    limit = settings.IMPRESSO_SOLR_EXEC_LIMIT
    max_loops = min(job.creator.profile.max_loops_allowed, settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS)

    # calculate remaining loops
    total = contents['response']['numFound']

    qtime = contents['responseHeader']['QTime']
    page = skip / limit + 1
    loops = min(math.ceil(total / limit), max_loops)
    progress = page / loops

    logger.info('  export_query_as_csv, numFound: %s' % total)
    logger.info('  export_query_as_csv, loops needed: {0}, allocated: {1}'.format(math.ceil(total / limit), loops))

    taskstate = 'ERROR'

    if total == 0:
        taskstate = 'SUCCESS'
        job.status = Job.DONE
        logger.info('  export_query_as_csv, nothing to do!' % total)
    else:
        logger.info('  export_query_as_csv, page: %s / %s' % (page, loops))
        with open(job.attachment.upload.path, mode='a', encoding='utf-8') as csvfile:
            w = csv.DictWriter(csvfile,  delimiter=';', fieldnames=settings.IMPRESSO_SOLR_ARTICLE_PROPS.split(',') + ['[total:{0},available:{1}]'.format(total, loops*limit)])
            if page == 1:
                w.writeheader()
            # write the first page already.
            w.writerows(map(solr_doc_to_article, contents['response']['docs']))
        # next loop!
        if page < loops:
            taskstate = 'PROGRESS'
            job.status = Job.RUN
            # call the same function and
            export_query_as_csv_progress.delay(
                job_id=job.pk,
                query=query,
                skip=skip + limit,
            )
        else:
            taskstate = 'SUCCESS'
            job.status = Job.DONE

    # update job status and meta
    meta = job.get_task_meta(taskname='test', progress=progress, extra = {
        'total': total,
        'skip': skip,
        'limit': limit,
        'page': page,
        'loops': loops,
        'query': query,
        'attachment': job.attachment.upload is not None,
    })
    job.extra = json.dumps(meta)
    job.save()
    # update state
    self.update_state(state = taskstate, meta = meta)
    # return job, to be seen in info
    return serializers.serialize('json', (job,))


@app.task(bind=True)
def export_query_as_csv(self, query, user_id, description):
    # save current job then start export_query_as_csv task.
    job = Job.objects.create(
        type=Job.EXPORT_QUERY_AS_CSV,
        creator_id=user_id,
        description=description,
    );

    attachment = Attachment.create_from_job(job, extension='csv')

    export_query_as_csv_progress.delay(job_id=job.pk, query=query)
    # return job, to be seen in info
    return serializers.serialize('json', (job,))





@app.task(bind=True, autoretry_for=(Exception,), exponential_backoff=2, retry_kwargs={'max_retries': 5}, retry_jitter=True)
def store_collectable_items(self, job_id, collection_id, skip=0, limit=50, taskname='store_collectable_items', method='add_to_index', items_ids=None):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    # get the collection!
    collection = Collection.objects.get(pk=collection_id)

    # get the collection status
    items = CollectableItem.objects.filter(
        collection = collection,
        content_type = CollectableItem.ARTICLE,
        indexed = False if method == 'add_to_index' else True,
    )

    if items_ids:
        items = items.filter(item_id__in=items_ids)

    total = items.count()

    logger.info('n. of items to store: %s' %  total)

    if total == 0:
        # nothing to do! return an error
        progress = 0
        loops = 0
        page = -1
        items_ids = []
    else:
        loops = math.ceil(total / limit)
        page = skip / limit + 1
        progress = page / loops
        # get the collectableItems ids in the collection
        items_ids = items.values_list('item_id', flat=True)[0:limit]
        logger.info('items_ids: %s' %  items_ids)
        # logger.info('skip: %s; limit: %s' % (skip,limit))
        # add items to the index
        if method == 'add_to_index':
            d = collection.add_items_to_index(items_ids=items_ids)
            items_ids_to_add = [doc.get('id') for doc in d.get('docs')]
            CollectableItem.objects.filter(
                collection = collection,
                item_id__in=items_ids_to_add
            ).update(indexed=True)
        else:
            collection.remove_items_to_index(items_ids=items_ids)

    if page == loops:
        taskstate = 'SUCCESS'
        job.status = Job.DONE
    elif page == -1:
        taskstate = 'ERROR'
        job.status = Job.ERR
    else:
        taskstate = 'PROGRESS'
        job.status = Job.RUN
        # queue job.
        store_collectable_items.delay(
            job_id = job.pk,
            collection_id = collection.pk,
            skip = int(page * limit),
            taskname = taskname
        )

    meta = job.get_task_meta(taskname=taskname, progress=progress, extra = {
        'total': total,
        'skip': skip,
        'limit': limit,
        'page': page,
        'loops': loops,
        'collection_id': collection.pk,
        'ids': [id for id in items_ids],
    })
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
    meta = {
        'task': 'sync_collection_in_solr',
        'progress': 0,
        'job_id': job.pk,
        'job_status': job.status,
        'user_id': collection.creator.pk,
        'user_uid': collection.creator.profile.uid,
    }

    job.extra = json.dumps(meta)
    job.save()
    # if alles gut
    self.update_state(state = "INIT", meta = meta)

    return serializers.serialize('json', (job,))


@app.task(bind=True)
def store_selected_collectable_items(self, collection_id, items_ids=[]):
    # get the collection
    collection = Collection.objects.get(pk=collection_id)
    # save current job!
    job = Job.objects.create(
        type=Job.SYNC_SELECTED_COLLECTABLE_ITEMS_TO_SOLR,
        creator=collection.creator
    );
    logger.info('selected items to store: %s' %  items_ids)

    meta = {
        'task': 'sync_selected_collectable_items_to_solr',
        'progress': 0,
        'job_id': job.pk,
        'job_status': job.status,
        'user_id': collection.creator.pk,
        'user_uid': collection.creator.profile.uid,
    }

    job.extra = json.dumps(meta)
    job.save()
    # if alles gut
    self.update_state(state = "INIT", meta = meta)
    # start update chain
    store_collectable_items.delay(
        job_id = job.pk,
        collection_id = collection.pk,
        items_ids = items_ids
    )

    return serializers.serialize('json', (job,))



@app.task(bind=True)
def count_items_in_collection(self, collection_id):
    # get the collection
    collection = Collection.objects.get(pk=collection_id)

    # count the items, per content type
    items = CollectableItem.objects.filter(
        collection = collection,
        content_type = CollectableItem.ARTICLE
    )

    count = items.count()
    items_ids = items.values_list('item_id', flat=True)

    print('  items count: %s' % count)
    print('  items sample: %s' % ','.join(items_ids[:3]))
    # save collection count
    collection.count_items = count
    collection.save()


@app.task(bind=True)
def execute_solr_query(self, query, fq, job_id, collection_id, content_type, skip=0):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    # get limit from settings
    limit = settings.IMPRESSO_SOLR_EXEC_LIMIT
    max_loops = min(job.creator.profile.max_loops_allowed, settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS)

    print('  execute_solr_query, q=%s' % query)
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
    loops = min(math.ceil(total / limit), max_loops)

    logger.info('  execute_solr_query, numFound: %s' % total)
    logger.info('  execute_solr_query, loops needed: %s' % math.ceil(total / limit))
    logger.info('  execute_solr_query, loops: %s' % loops)

    meta = {
        'task': 'execute_solr_query',
        'progress': 0,
        'job_id': job.pk,
        'user_id': job.creator.pk,
        'user_uid': job.creator.profile.uid,
        'extra': {
            'q': query,
            'QTime': qtime,
            'total': total,
            # here we put the actual loops needed.
            'loops':  loops,
            'realloops': math.ceil(total / limit),
            'maxloops': max_loops,
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
            fq = fq,
            job_id = job_id,
            collection_id = collection_id,
            content_type = content_type,
            skip = (skip + limit)
        )
    else:
        job.status = Job.DONE

    meta['job_status'] = job.status
    job.extra = json.dumps(meta)
    job.save()

    # update state
    self.update_state(state = "PROGRESS" if job.status == Job.RUN else "SUCCESS", meta = meta)

    if job.status == Job.DONE:
        count_items_in_collection.delay(collection_id = collection_id)
        store_collection.delay(collection_id = collection_id)

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
def add_to_collection_from_query(self, collection_id, user_id, query, content_type, fq=None):
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
        'user_uid': collection.creator.profile.pk,
    })

    # execute premiminary query
    execute_solr_query.delay(
        query  = query,
        fq = fq,
        job_id = job.pk,
        collection_id = collection.pk,
        content_type = content_type,
    )

    return serializers.serialize('json', (job,))
