from __future__ import absolute_import

from os.path import basename

import json, time, math, csv
import requests

from django.core import serializers
from django.conf import settings
from django.db.utils import IntegrityError

from .celery import app
from .models import Job, Collection, CollectableItem, SearchQuery, Attachment
from .solr import find_all, solr_doc_to_article

from celery.utils.log import get_task_logger

from zipfile import ZipFile, ZIP_DEFLATED

logger = get_task_logger(__name__)

TASKSTATE_INIT = 'INIT'
TASKSTATE_PROGRESS = 'PROGRESS'
TASKSTATE_SUCCESS = 'SUCCESS'
TASKSTATE_STOPPED = 'STOPPED'

def update_job_completed(task, job, extra={}):
    '''
    Call update_job_progress for one last time. This method sets the job status to Job.DONE
    '''
    job.status = Job.DONE
    job.save()
    update_job_progress(task=task, job=job, taskstate=TASKSTATE_SUCCESS, progress=1.0, extra=extra)

def update_job_progress(task, job, progress, taskstate=TASKSTATE_PROGRESS, extra={}):
    '''
    generic function to update a job
    '''
    meta = job.get_task_meta(taskname=task.name, progress=progress, extra=extra)
    job.extra = json.dumps(meta)
    job.save()
    task.update_state(state=taskstate, meta=meta)

def is_task_stopped(task, job, progress, extra={}):
    '''
    Check if a job has been stopped by the user. If yes, this methos sets the job status to STOPPED for you,
    then call update_job_progress one last time.
    '''
    if job.status != Job.STOP:
        return False
    job.status = Job.RIP
    extra.update({
        'stopped': True
    })
    update_job_progress(task=task, job=job, progress=progress, taskstate=TASKSTATE_STOPPED, extra=extra)
    return True

def get_job_stats(job, skip, limit, total):
    limit = min(limit, settings.IMPRESSO_SOLR_EXEC_LIMIT)
    max_loops = min(job.creator.profile.max_loops_allowed, settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS)
    page = 1 + skip / limit
    loops = min(math.ceil(total / limit), max_loops)
    progress = page / loops if loops > 0 else 1.0 # NOthing to do if there's no loops...
    logger.info('[job:{}] get_job_stats: page:{}, limit:{}, total:{}, progress:{}, loops:{}, max_loops:{}, user_loops:{}, settings_loops: {}'.format(
        job.pk,
        page,
        limit,
        total,
        progress,
        loops,
        max_loops,
        job.creator.profile.max_loops_allowed,
        settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
    ))
    return page, loops, progress

def get_collection_as_obj(collection):
    return {
        'id': collection.pk,
        'name': collection.name,
        'description': collection.description,
        'status': collection.status,
        'date_created': collection.date_created.isoformat()
    }

@app.task(bind=True)
def echo(self, message):
    print('Request: {0!r}'.format(self.request))
    print('Message: {0}'.format(message))
    return message


@app.task(bind=True)
def test_progress(self, job_id, sleep=5, pace=0.01, progress=0.0):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    extra = {
        'pace': pace,
        'sleep': sleep,
    }

    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        logger.info('TEST job id:{} STOPPED for user id:{}. Bye!'.format(job.pk, job.creator.pk))
        return

    job.status = Job.RUN
    # update pregress accordingly
    update_job_progress(task=self, job=job, progress=progress, extra=extra)

    if progress < 1.0:
        logger.info('TEST job id:{} still running PROGRESS {} for user id:{}...!'.format(
            job.pk,
            progress,
            job.creator.pk,
        ))
        # do heavy stuff during this time
        time.sleep(sleep)
        # call the same function right after
        test_progress.delay(
            job_id=job.pk,
            sleep=sleep,
            pace=pace,
            progress=progress + pace
        )
    else:
        logger.info('TEST job id:{} DONE for user id:{}'.format(
            job.pk,
            job.creator.pk,
        ))
        update_job_completed(task=self, job=job, extra=extra)


@app.task(bind=True)
def test(self, user_id):
    # save current job then start test_progress task.
    job = Job.objects.create(
        type=Job.TEST,
        creator_id=user_id
    );
    logger.info('TEST job id:{} launched for user id:{}...'.format(job.pk, user_id))
    # stat loop
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0)
    test_progress.delay(job_id=job.pk)




@app.task(bind=True, autoretry_for=(Exception,), exponential_backoff=2, retry_kwargs={'max_retries': 5}, retry_jitter=True)
def export_query_as_csv_progress(self, job_id, query, search_query_id, query_hash='', skip=0, limit=100):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    extra = {
        'query': query_hash,
        'search_query_id': search_query_id,
    }
    # do find_all
    logger.info('[job:{}] Executing query: {}'.format(job.pk, query))
    logger.info('[job:{}] User: {} is_staff:{}'.format(job.pk, job.creator.pk, job.creator.is_staff))

    contents = find_all(
        q=query,
        fl=settings.IMPRESSO_SOLR_FIELDS,
        skip=skip,
        logger=logger
    )

    total = contents['response']['numFound']
    logger.info('[job:{}] Query success: {} results found'.format(job.pk, total))
    # generate extra from job stats
    page, loops, progress = get_job_stats(job=job, skip=skip, limit=limit, total=total)

    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        logger.info('[job:{}] Task STOPPED. Bye!'.format(job.pk))
        return

    if total == 0:
        update_job_completed(task=self, job=job, extra=extra)
        return
    # update status to RUN
    job.status = Job.RUN

    extra.update({
        'qtime': contents['responseHeader']['QTime'],
        'attachment': job.attachment.upload is not None,
    })

    logger.info('[job:{}] Opening file in APPEND mode: {}'.format(job.pk, job.attachment.upload.path))

    def doc_filter_contents(doc):
        doc_year = int(doc['year'])
        if 'is_content_available' in doc:
            if doc['is_content_available'] != "true":
                doc['content'] = ''
                doc['is_content_available'] = ''
            else:
                doc['is_content_available'] = 'y'
        elif doc_year >= settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR:
            doc['content'] = ''
        return doc

    with open(job.attachment.upload.path, mode='a', encoding='utf-8') as csvfile:
        w = csv.DictWriter(csvfile,  delimiter=';', fieldnames=settings.IMPRESSO_SOLR_ARTICLE_PROPS.split(',') + ['[total:{0},available:{1}]'.format(total, loops*limit)])
        if page == 1:
            w.writeheader()
        rows = map(solr_doc_to_article, contents['response']['docs'])
        if not job.creator.is_staff:
            rows = map(doc_filter_contents, rows)
        # remove content for the rows if their date is below a threshold

        w.writerows(rows)

    # update pregress accordingly
    update_job_progress(task=self, job=job, progress=progress, extra=extra)
    # next loop!
    if page < loops:
        export_query_as_csv_progress.delay(
            job_id=job.pk,
            query=query,
            query_hash=query_hash,
            search_query_id=search_query_id,
            skip=page*limit,
            limit=limit,
        )
    else:
        zipped = '%s.zip' % job.attachment.upload.path;
        logger.info('[job:{}] Loops completed, creating the corresponding zip file: {}.zip ...'.format(job.pk, job.attachment.upload.path))
        with ZipFile(zipped, 'w', ZIP_DEFLATED) as zip:
            zip.write(job.attachment.upload.path, basename(job.attachment.upload.path))
        logger.info('[job:{}] Loops completed, corresponding zip file: {}.zip created.'.format(job.pk, job.attachment.upload.path))
        # substitute the job attachment
        job.attachment.upload.name = '%s.zip' % job.attachment.upload.name;
        job.attachment.save()
        # if everything is fine, delete the original file
        update_job_completed(task=self, job=job, extra=extra)


@app.task(bind=True)
def export_query_as_csv(self, user_id, query, description='', query_hash='', search_query_id=None):
    # save current job then start export_query_as_csv task.
    job = Job.objects.create(
        type=Job.EXPORT_QUERY_AS_CSV,
        creator_id=user_id,
        description=description,
    );

    attachment = Attachment.create_from_job(job, extension='csv')

    if not search_query_id:
        search_query, created = SearchQuery.objects.get_or_create(
            id=SearchQuery.generate_id(creator_id=user_id, query=query_hash),
            defaults={
                'data': query_hash,
                'description': description,
                'creator_id':user_id
            }
        )
        print(search_query)
        print(search_query.pk)
        search_query_id = search_query.pk
    logger.info('[job:{}] started, search_query_id:{} created:{}...'.format(job.pk, search_query_id, created))

    # add query to extra. Job status should be INIT
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0, extra={
        'query': query_hash,
        'search_query_id': search_query_id,
    })

    export_query_as_csv_progress.delay(job_id=job.pk, query=query, query_hash=query_hash, search_query_id=search_query_id)






@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 5}, retry_jitter=True)
def store_collectable_items(self, job_id, collection_id, skip=0, limit=50, taskname='store_collectable_items', method='add_to_index', items_ids=None):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    # get the collection!
    collection = Collection.objects.get(pk=collection_id)
    extra = {
        'collection_id': collection_id,
        'collection': get_collection_as_obj(collection),
    }
    # get the collection status
    items = CollectableItem.objects.filter(
        collection = collection,
        content_type = CollectableItem.ARTICLE,
        indexed = False if method == 'add_to_index' else True,
    )

    if items_ids:
        items = items.filter(item_id__in=items_ids)

    total = items.count()

    logger.info('Collection(pk:{}) n. of items to store: {} (skip: {}; limit: {}; method: {})'.format(
        collection.pk,
        total,
        skip,
        limit,
        method,
    ))

    # generate extra from job stats
    page, loops, progress = get_job_stats(job=job, skip=skip, limit=limit, total=total)

    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        logger.info('[job:{}] Task STOPPED. Bye!'.format(job.pk))
        return

    if total == 0:
        logger.info('Collection(pk:{}) nothing to do!'.format(collection.pk))
        update_job_completed(task=self, job=job, extra=extra)
        return
    # update status to RUN
    job.status = Job.RUN

    # update pregress accordingly
    update_job_progress(task=self, job=job, progress=progress)

    # get the collectableItems ids in the collection
    items_ids = items.values_list('item_id', flat=True)[0:limit]
    logger.info('Collection(pk:{}) store {} items_ids, first three ids: {}'.format(
        collection.pk,
        len(items_ids),
        items_ids[:3],
    ))

    # add items to the index
    if method == 'add_to_index':
        result = collection.add_items_to_index(items_ids=items_ids, logger=logger)
        logger.info('Collection(pk:{}) n.items to update in db with (indexed=True): {}, first three ids: {}, added to solr: {}'.format(
            collection.pk,
            len(result.get('docs')),
            result.get('docs')[:3],
            len(result.get('todos')),
        ))
        items_ids_to_add = [doc.get('id') for doc in result.get('docs')]
        # perform query
        indexed = CollectableItem.objects.filter(
            collection = collection,
            item_id__in=items_ids_to_add
        ).update(indexed=True)

        logger.info('Collection(pk:{}) success, {} items updated in db.'.format(
            collection.pk,
            indexed,
        ))
    else:
        collection.remove_items_to_index(items_ids=items_ids)

    if page < loops:
        store_collectable_items.delay(
            job_id = job.pk,
            collection_id = collection.pk,
            skip = int(page * limit),
            taskname = taskname,
            items_ids=items_ids,
        )
    else:
        update_job_completed(task=self, job=job, extra=extra)



@app.task(bind=True)
def store_collection(self, collection_id, items_ids=None):
    # get the collection
    collection = Collection.objects.get(pk=collection_id)
    # save current job!
    job = Job.objects.create(
        type=Job.SYNC_COLLECTION_TO_SOLR,
        creator=collection.creator
    );

    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0, extra={
        'collection': get_collection_as_obj(collection),
    })

    logger.info('Collection(pk:{}) delay store_collectable_items, with items: {}'.format(
        collection.pk,
        items_ids,
    ))
    # start update chain
    store_collectable_items.delay(
        job_id = job.pk,
        collection_id = collection.pk,
        items_ids=items_ids,
    )


@app.task(bind=True)
def count_items_in_collection(self, collection_id):
    # get the collection
    collection = Collection.objects.get(pk=collection_id)
    count_in_solr = collection.update_count_items(logger=logger)
    count_in_db = CollectableItem.objects.filter(collection = collection).count()
    logger.info('Collection(pk:{}) received {} in solr, {} in db.'.format(
        collection.pk,
        count_in_solr,
        count_in_db,
    ))


@app.task(bind=True)
def execute_solr_query(self, query, fq, job_id, collection_id, content_type, skip=0, limit=100):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    # get the collection so that we can see its status
    collection = Collection.objects.get(pk=collection_id)
    if collection.status == Collection.DELETED:
        logger.info('Collection {} status has been set to DEL, skipping.'.format(collection_id, collection.status))
        update_job_completed(task=self, job=job, extra={
            'collection': get_collection_as_obj(collection),
            'cleared': True,
            'reason': 'Collection has status:DEL'
        })
        return

    logger.info('Collection {}(status:{}), saving query: q={}'.format(collection_id, collection.status, query))
    # now execute solr query, along with first `limit` rows
    res = requests.post(settings.IMPRESSO_SOLR_URL_SELECT, auth=settings.IMPRESSO_SOLR_AUTH, params={
        'start': int(skip),
        'rows': int(limit),
        'fl': '%s,score' % settings.IMPRESSO_SOLR_ID_FIELD,
        'wt': 'json',
        'sort': 'id ASC',
        'hl': 'off',
    }, data={
        'q': query
    })
    # should repeat until this gets None
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(res.text)
        raise
    contents = res.json()
    total = contents['response']['numFound']
    start = contents['response']['start']
    # generate extra from job stats
    page, loops, progress = get_job_stats(job=job, skip=skip, limit=limit, total=total)
    extra = {
        'total': total,
        'skip': skip,
        'limit': limit,
        'page': page,
        'loops': loops,
        'query': query,
        'qtime': contents['responseHeader']['QTime'],
        'qheaders': contents['responseHeader'],
        'collection_id': collection_id,
        'collection': get_collection_as_obj(collection),
    }
    # check if the job has been stopped
    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        logger.info('Collection(pk:{}), task STOPPED. Bye!'.format(collection_id))
        return

    job.status = Job.RUN

    logger.info('Collection(pk:{}), total: {}, start: {}, loop {} of {} (using {} skip, {} limit), headers: {}'.format(
        collection_id,
        total,
        start,
        page,
        loops,
        skip,
        limit,
        contents['responseHeader'],
    ))

    # is there actually something to do?
    if total < 1:
        logger.info('Collection(pk:{}), query returned empty results. Bye!'.format(collection_id))
        update_job_completed(task=self, job=job, extra=extra)
        return

    items = [*map(lambda doc: {'id': doc.get(settings.IMPRESSO_SOLR_ID_FIELD),'score': doc.get('score')}, contents['response']['docs'])]
    items_ids = [*map(lambda doc: doc.get('id'), items)]

    logger.info('Collection(pk:{}), bulk_create CollectableItem from {} items_ids'.format(
        collection_id,
        len(items_ids),
    ))

    try:
        CollectableItem.objects.bulk_create(map(
            lambda item_id: CollectableItem(
                item_id = item_id,
                content_type = content_type,
                collection = collection,
            ),
            items_ids
        ), ignore_conflicts=True)
    except IntegrityError as e:
        logger.exception(e)
        extra.update({
            'warnings':str(e)
        })

    # The cool class method which performs the actual update of solr index.
    collection.add_items_to_index(items_ids=items_ids, logger=logger)

    # update pregress accordingly
    update_job_progress(task=self, job=job, progress=progress, extra=extra)

    if page < loops:
        logger.info('Collection {}, launching next loop...'.format(collection_id))
        # once it's done, go on with the following execution!
        execute_solr_query.delay(
            query = query,
            fq = fq,
            job_id = job_id,
            collection_id = collection_id,
            content_type = content_type,
            skip = (skip + limit),
            limit = limit,
        )
    else:
        logger.info('Collection {}, last stand: count!'.format(collection_id))
        count_items_in_collection.delay(collection_id = collection_id)
        # store_collection.delay(collection_id = collection_id)
        update_job_completed(task=self, job=job, extra=extra)


@app.task(bind=True)
def remove_collection(self, collection_id, user_id):
    '''
    Remove a collection. Its status should be set to DEL
    '''
    # check that the collection (still) exists!
    collection = Collection.objects.get(pk=collection_id, creator__id=user_id, status=Collection.DELETED);
    # save current job!
    job = Job.objects.create(
        type=Job.DELETE_COLLECTION,
        creator=collection.creator
    );
    logger.info('Collection %s, launch "remove_from_collection" task...' %  collection.pk)
    # stat loop
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0, extra={
        'collection': get_collection_as_obj(collection),
    })
    remove_from_collection.delay(
        job_id = job.pk,
        collection_id = collection.pk,
        user_id = user_id,
    )


@app.task(bind=True, autoretry_for=(Exception,), exponential_backoff=2, retry_kwargs={'max_retries': 5}, retry_jitter=True)
def remove_from_collection(self, job_id, collection_id, user_id, skip=0, limit=100, items_ids=[]):
    job = Job.objects.get(pk=job_id) # get the job so that we can update its status
    collection = Collection.objects.get(pk=collection_id) # get the collection!
    items = CollectableItem.objects.filter(
        collection = collection,
    )
    # calculate total
    if items_ids:
        items = items.filter(item_id__in=items_ids)
    total = items.count()
    # generate extra from job stats
    page, loops, progress = get_job_stats(job=job, skip=skip, limit=limit, total=total)
    extra = {
        'total': total,
        'skip': skip,
        'limit': limit,
        'page': page,
        'loops': loops,
        'collection_id': collection.pk,
        'collection': get_collection_as_obj(collection),
    }

    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        logger.info('Collection {}, task STOPPED. Bye!'.format(collection.pk))
        return
    # update status if it is not stopped
    job.status = Job.RUN

    logger.info('Collection {}, {} total CollectableItems, loop {} of {} (using {} skip, {} limit)'.format(
        collection.pk,
        total,
        page,
        loops,
        skip,
        limit,
    ))

    # perform deletion of collections uids in SOLR documents:
    current_items_ids = items.values_list('item_id', flat=True)[int(skip):int(limit + skip)]
    logger.info('Collection {}, n. of current_items_ids: {}'.format(collection.pk, len(current_items_ids)))

    if not current_items_ids:
        update_job_completed(task=self, job=job, extra=extra)
        return

    # The cool class method which performs the actual deletion from solr index.
    collection.remove_items_from_index(items_ids=list(current_items_ids), logger=logger)
    # Now we can safely remove the collectableItems.
    result = CollectableItem.objects.filter(collection=collection).filter(item_id__in=list(current_items_ids)).delete()
    logger.info('Collection {}, items_ids: {} REMOVED! result {}'.format(collection.pk, list(current_items_ids), result))
    # update pregress accordingly
    update_job_progress(task=self, job=job, progress=progress, extra=extra)

    if page < loops:
        remove_from_collection.delay(
            job_id=job.pk,
            collection_id=collection.pk,
            user_id=user_id,
            limit=limit,
            skip=page*limit
        )
    else:
        print('update_job_completed', page, loops)
        collection.delete()
        update_job_completed(task=self, job=job, extra=extra)


@app.task(bind=True)
def add_to_collection_from_query(self, collection_id, user_id, query, content_type, fq=None):
    # check that the collection exists!
    collection = Collection.objects.get(pk=collection_id, creator__id=user_id);

    # save current job!
    job = Job.objects.create(
        type=Job.BULK_COLLECTION_FROM_QUERY,
        creator=collection.creator
    );
    # add collection to extra.
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0, extra={
        'collection': get_collection_as_obj(collection),
    })
    # execute premiminary query
    execute_solr_query.delay(
        query  = query,
        fq = fq,
        job_id = job.pk,
        collection_id = collection.pk,
        content_type = content_type,
    )
