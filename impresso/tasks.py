from __future__ import absolute_import

from os.path import basename

import os
import json
import time
import math
import csv

from django.conf import settings

from .celery import app
from .models import Job, Collection, CollectableItem, SearchQuery, Attachment
from .solr import find_all, solr_doc_to_article

from celery.utils.log import get_task_logger

from zipfile import ZipFile, ZIP_DEFLATED

from .utils.tasks import (
    TASKSTATE_INIT,
    get_pagination,
    update_job_progress,
    update_job_completed,
    is_task_stopped,
    mapper_doc_remove_private_collections,
    mapper_doc_redact_contents,
)
from .utils.tasks.collection import sync_collections_in_tr_passages
from .utils.tasks.textreuse import remove_collection_from_tr_passages
from .utils.tasks.textreuse import add_tr_passages_query_results_to_collection
from .utils.tasks.collection import delete_collection, sync_query_to_collection
from .utils.tasks.collection import METHOD_ADD_TO_INDEX, METHOD_DEL_FROM_INDEX
from .utils.tasks.account import send_emails_after_user_registration
from .utils.tasks.account import send_emails_after_user_activation
from .utils.tasks.account import send_email_password_reset
from .utils.tasks.userBitmap import update_user_bitmap

logger = get_task_logger(__name__)


def get_collection_as_obj(collection):
    return {
        "id": collection.pk,
        "name": collection.name,
        "description": collection.description,
        "status": collection.status,
        "date_created": collection.date_created.isoformat(),
    }


@app.task(bind=True)
def echo(self, message):
    logger.info("Request: f{message}")
    response = f"You: {message}"
    return response


@app.task(bind=True)
def test_progress(self, job_id, sleep=100, pace=0.01, progress=0.0):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    extra = {
        "pace": pace,
        "sleep": sleep,
    }

    if is_task_stopped(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    ):
        return

    update_job_progress(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    )

    if progress < 1.0:
        # do heavy stuff during this time
        time.sleep(sleep)
        # call the same function right after
        test_progress.delay(
            job_id=job.pk, sleep=sleep, pace=pace, progress=progress + pace
        )
        return
    update_job_completed(task=self, job=job, extra=extra, logger=logger)


@app.task(bind=True)
def test(self, user_id, sleep=1, pace=0.05):
    # save current job then start test_progress task.
    job = Job.objects.create(type=Job.TEST, status=Job.RUN, creator_id=user_id)
    logger.info(f"[job:{job.pk} user:{user_id}] launched!")
    # stat loop
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0)
    test_progress.delay(job_id=job.pk, sleep=sleep, pace=pace)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def export_query_as_csv_progress(
    self, job_id, query, search_query_id, query_hash="", skip=0, limit=100
):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    extra = {
        "query": query_hash,
        "search_query_id": search_query_id,
    }
    # do find_all
    logger.info(f"[job:{job.pk} user:{job.creator.pk}] launched! query:{query_hash}")

    contents = find_all(
        q=query, fl=settings.IMPRESSO_SOLR_FIELDS, skip=skip, logger=logger
    )
    total = contents["response"]["numFound"]
    qtime = contents["responseHeader"]["QTime"]
    # generate extra from job stats
    page, loops, progress, max_loops = get_pagination(
        skip=skip, limit=limit, total=total, job=job
    )
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] "
        f" total:{total} in {qtime} -"
        f" loops:{loops} - max_loops:{max_loops} -"
        f" page:{page} - progress:{progress} -"
    )

    if is_task_stopped(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    ):
        return

    if total == 0:
        update_job_completed(task=self, job=job, extra=extra, logger=logger)
        return

    extra.update(
        {
            "qtime": contents["responseHeader"]["QTime"],
            "attachment": job.attachment.upload is not None,
        }
    )

    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] Opening file in APPEND mode:"
        f"{job.attachment.upload.path}"
    )

    with open(job.attachment.upload.path, mode="a", encoding="utf-8") as csvfile:
        w = csv.DictWriter(
            csvfile,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
            fieldnames=settings.IMPRESSO_SOLR_ARTICLE_PROPS
            + ["[total:{0},available:{1}]".format(total, loops * limit)],
        )
        if page == 1:
            w.writeheader()
        rows = map(solr_doc_to_article, contents["response"]["docs"])
        # remove collections for the rows if they do not start with the job creator id
        rows = [mapper_doc_remove_private_collections(doc, job=job) for doc in rows]

        if not job.creator.is_staff:
            rows = map(mapper_doc_redact_contents, rows)

        w.writerows(rows)

    # update status to RUN
    job.status = Job.RUN
    # update pregress accordingly
    update_job_progress(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    )
    # next loop!
    if page < loops:
        export_query_as_csv_progress.delay(
            job_id=job.pk,
            query=query,
            query_hash=query_hash,
            search_query_id=search_query_id,
            skip=page * limit,
            limit=limit,
        )
    else:
        zipped = "%s.zip" % job.attachment.upload.path
        uncompressed = job.attachment.upload.path
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] creating the corresponding zip file: "
            f"{zipped} ..."
        )
        with ZipFile(zipped, "w", ZIP_DEFLATED) as zip:
            zip.write(job.attachment.upload.path, basename(job.attachment.upload.path))
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] success, corresponding zip file: {zipped} created."
        )
        # substitute the job attachment
        job.attachment.upload.name = "%s.zip" % job.attachment.upload.name
        job.attachment.save()
        # if everything is fine, delete the original file
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] deleting original csv file: {uncompressed} ..."
        )
        # // remove CSV file
        if os.path.exists(uncompressed):
            os.remove(uncompressed)
        else:
            print(f"The file does not exist: {uncompressed}")
            logger.warning(
                f"[job:{job.pk} user:{job.creator.pk}] Note: the file does not exist: {uncompressed}"
            )
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] success, original csv file: {uncompressed} deleted."
        )
        update_job_completed(task=self, job=job, extra=extra, logger=logger)


@app.task(bind=True)
def export_query_as_csv(
    self, user_id, query, description="", query_hash="", search_query_id=None
):
    # save current job then start export_query_as_csv task.
    job = Job.objects.create(
        type=Job.EXPORT_QUERY_AS_CSV,
        creator_id=user_id,
        description=description,
    )

    attachment = Attachment.create_from_job(job, extension="csv")

    if not search_query_id:
        search_query, created = SearchQuery.objects.get_or_create(
            id=SearchQuery.generate_id(creator_id=user_id, query=query_hash),
            defaults={
                "data": query_hash,
                "description": description,
                "creator_id": user_id,
            },
        )

        search_query_id = search_query.pk
    logger.info(
        "[job:{}] started, search_query_id:{} created:{}, attachment:{}...".format(
            job.pk, search_query_id, created, attachment.upload.path
        )
    )

    # add query to extra. Job status should be INIT
    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        extra={
            "query": query_hash,
            "search_query_id": search_query_id,
        },
    )

    export_query_as_csv_progress.delay(
        job_id=job.pk,
        query=query,
        query_hash=query_hash,
        search_query_id=search_query_id,
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def store_collection_progress(
    self, job_id, collection_id, items_ids, skip, limit, content_type, method
):
    job = Job.objects.get(pk=job_id)
    collection = Collection.objects.get(pk=collection_id)
    query = " OR ".join(map(lambda id: f"id:{id}", items_ids))
    extra = {
        "collection_id": collection_id,
        "collection": get_collection_as_obj(collection),
        "items_ids": items_ids,
        "query": query,
        "method": method,
    }
    if collection.status == Collection.DELETED:
        logger.info(f"Collection {collection_id} status is DEL, exit!")
        extra.update({"cleared": True, "reason": "Collection has status:DEL"})
        update_job_completed(task=self, job=job, extra=extra)
        return
    logger.info(
        f"Collection {collection_id}(status:{collection.status}), "
        f"saving query: q={query}"
    )
    page, loops, progress, total, allowed = sync_query_to_collection(
        collection_id=collection_id,
        query=query,
        content_type=content_type,
        skip=skip,
        limit=limit,
        method=method,
        logger=logger,
    )
    extra.update(
        {
            "total": total,
            "allowed": allowed,
        }
    )
    if progress < 1.0:
        if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
            return
        update_job_progress(task=self, job=job, progress=progress, extra=extra)
        store_collection_progress.delay(
            job_id=job_id,
            collection_id=collection_id,
            items_ids=items_ids,
            skip=skip + limit,
            limit=limit,
            content_type=content_type,
            method=method,
        )
    else:
        update_job_completed(task=self, job=job, extra=extra)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def store_collection(
    self, collection_id, items_ids=[], method=METHOD_ADD_TO_INDEX, content_type="A"
):
    """
    Add items_ids to an existing collection.
    """
    collection = Collection.objects.get(pk=collection_id)
    if method == METHOD_DEL_FROM_INDEX:
        job_type = Job.REMOVE_FROM_SOLR
    else:
        job_type = Job.SYNC_COLLECTION_TO_SOLR
    job = Job.objects.create(type=job_type, creator=collection.creator, status=Job.RUN)

    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        extra={
            "collection": get_collection_as_obj(collection),
            "items": items_ids,
            "method": method,
        },
    )

    logger.info(f"Collection(pk:{collection.pk}) " f"items={items_ids} method={method}")
    # start update chain
    store_collection_progress.delay(
        job_id=job.pk,
        collection_id=collection.pk,
        items_ids=items_ids,
        method=method,
        content_type=content_type,
        skip=0,
        limit=100,
    )


@app.task(bind=True)
def count_items_in_collection(self, collection_id):
    # get the collection
    collection = Collection.objects.get(pk=collection_id)
    count_in_solr = collection.update_count_items(logger=logger)
    count_in_db = CollectableItem.objects.filter(collection=collection).count()
    logger.info(
        "Collection(pk:{}) received {} in solr, {} in db.".format(
            collection.pk,
            count_in_solr,
            count_in_db,
        )
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def add_to_collection_from_query(
    self, collection_id, user_id, query, content_type, fq=None, serialized_query=None
):
    # check that the collection exists and user has access.
    collection = Collection.objects.get(pk=collection_id, creator__id=user_id)
    # save current job!
    job = Job.objects.create(
        type=Job.BULK_COLLECTION_FROM_QUERY, creator=collection.creator, status=Job.RUN
    )
    # add collection to extra.
    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        extra={
            "collection": get_collection_as_obj(collection),
            "query": query,
            "serializedQuery": serialized_query,
        },
    )
    # execute premiminary query
    add_to_collection_from_query_progress.delay(
        query=query,
        fq=fq,
        job_id=job.pk,
        collection_id=collection_id,
        content_type=content_type,
        serialized_query=serialized_query,
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def add_to_collection_from_query_progress(
    self,
    query,
    fq,
    job_id,
    collection_id,
    content_type,
    skip=0,
    limit=100,
    prev_progress=0.0,
    serialized_query=None,
):
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job, progress=prev_progress):
        return

    # get the collection so that we can see its status
    collection = Collection.objects.get(pk=collection_id)
    if collection.status == Collection.DELETED:
        logger.info(f"Collection {collection_id} status is DEL, exit!")
        update_job_completed(
            task=self,
            job=job,
            extra={
                "collection": get_collection_as_obj(collection),
                "query": query,
                "serializedQuery": serialized_query,
                "cleared": True,
                "reason": "Collection has status:DEL",
            },
        )
        return
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] "
        f"Collection {collection_id}(status:{collection.status})"
        f"saving query hash = {serialized_query}"
    )
    page, loops, progress, total, allowed = sync_query_to_collection(
        job=job,
        collection_id=collection_id,
        query=query,
        content_type=content_type,
        skip=skip,
        limit=limit,
        logger=logger,
    )
    extra = {
        "collection": get_collection_as_obj(collection),
        "total": total,
        "allowed": allowed,
        "query": query,
        "serializedQuery": serialized_query,
    }
    if progress < 1.0:
        if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
            return
        update_job_progress(task=self, job=job, progress=progress, extra=extra)
        logger.info(f"job({job.pk}) still running!")
        add_to_collection_from_query_progress.delay(
            query=query,
            fq=fq,
            job_id=job_id,
            collection_id=collection_id,
            content_type=content_type,
            skip=skip + limit,
            limit=limit,
            serialized_query=serialized_query,
        )
    else:
        logger.info(f"job({job.pk}) COMPLETED! Bye!")
        update_job_completed(task=self, job=job, extra=extra)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def remove_collection(self, collection_id, user_id):
    """
    Remove a collection only if its status is DEL
    """
    job = Job.objects.create(
        type=Job.DELETE_COLLECTION, creator_id=user_id, status=Job.RUN
    )
    # check that the collection (still) exists!
    try:
        collection = Collection.objects.get(pk=collection_id)
        # only if the creator is the owner and status is DEL
        collection_to_delete = (
            collection.status == Collection.DELETED and collection.creator.pk == user_id
        )
        collection_seralized = get_collection_as_obj(collection)
        logger.info(
            f"Collection found with pk={collection_id}, "
            f"status={collection_to_delete}"
        )
    except Collection.DoesNotExist:
        collection_seralized = {"pk": collection_id}
        collection_to_delete = True
        logger.info(
            f"Collection.DoesNotExist in DB with pk={collection_id}, removing on SOLR..."
        )
    if not collection_to_delete:
        logger.info(
            f"Cannot delete collection pk={collection_id}, please set it status=DEL!"
        )
        update_job_completed(task=self, job=job)
        return
    logger.info(f"Delete collection pk={collection_id}...")
    # stat loop
    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        extra={"collection": collection_seralized},
    )
    remove_collection_progress.delay(
        job_id=job.pk, collection_id=collection_id, user_id=user_id
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def remove_collection_progress(
    self,
    job_id,
    collection_id,
    user_id,
    skip=0,
    limit=100,
    progress=0.0,
):
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job, progress=progress):
        return
    page, loops, progress = delete_collection(collection_id=collection_id, limit=limit)
    update_job_progress(task=self, job=job, progress=progress, extra={})

    if progress < 1.0:
        logger.info(f"job({job.pk}) still running!")
        remove_collection_progress.delay(
            job_id=job.pk, collection_id=collection_id, user_id=user_id
        )
    else:
        logger.info(f"remove_collection_progress completed page={page} loops={loops}")
        try:
            removed = Collection.objects.get(pk=collection_id).delete()
            logger.info(f"Collection removed: {removed}")
        except Collection.DoesNotExist:
            logger.info("Collection has already been deleted from db. Bye!")
        remove_collection_in_tr.delay(collection_id=collection_id, user_id=user_id)
        update_job_completed(task=self, job=job)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def update_collections_in_tr_passages_progress(
    self, job_id, collection_prefix, progress=0.0, skip=0, limit=100
):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    extra = {}

    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        logger.info(f"job {job.pk} STOPPED, user id:{ job.creator.pk}. Bye!")
        return
    page, loops, progress = sync_collections_in_tr_passages(
        collection_id=collection_prefix, skip=skip, limit=limit
    )
    logger.info(
        f"job({job.pk}) running on prefix={collection_prefix}"
        f"{page}/{loops} {progress}%"
    )
    update_job_progress(task=self, job=job, progress=progress, extra=extra)

    if progress < 1.0:
        logger.info(f"job({job.pk}) still running!")
        update_collections_in_tr_passages_progress.delay(
            collection_prefix=collection_prefix, job_id=job.pk, skip=skip + limit
        )
    else:
        logger.info(f"job({job.pk}) COMPLETED! Bye!")
        update_job_completed(task=self, job=job, extra=extra)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def update_collections_in_tr_passages(self, collection_prefix, user_id=None):
    collections = Collection.objects.filter(
        pk__startswith=collection_prefix.replace("*", "")
    )
    total = collections.count()
    logger.info(f"Collections pk__startswith={collection_prefix}" f"count={total}")
    # save current job!
    job = Job.objects.create(
        type=Job.SYNC_COLLECTIONS_TO_SOLR_TR,
        creator_id=user_id if user_id else collections.first().creator.pk,
        status=Job.RUN,
    )
    # initialize job
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0)
    update_collections_in_tr_passages_progress.delay(
        collection_prefix=collection_prefix,
        job_id=job.pk,
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def remove_collection_in_tr(self, collection_id, user_id):
    try:
        collection = Collection.objects.get(pk=collection_id)
        collection_to_delete = collection.status == Collection.DELETED
        logger.info(
            f"Collection found with pk={collection_id}, "
            f"status={collection_to_delete}"
        )
    except Collection.DoesNotExist:
        collection_to_delete = True
        logger.info(f"Collection.DoesNotExist in DB with pk={collection_id}")
    # save current job!
    job = Job.objects.create(
        type=Job.REMOVE_COLLECTIONS_FROM_SOLR_TR, creator_id=user_id, status=Job.RUN
    )
    if not collection_to_delete:
        logger.info(f"Collection pk={collection_id} not marked as DEL!!")
        update_job_completed(task=self, job=job)
        return
    logger.info(f"Delete collection pk={collection_id} from TR index...")
    # initialize job
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0)
    remove_collection_in_tr_progress.delay(
        collection_id=collection_id, job_id=job.pk, skip=0, limit=100
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def remove_collection_in_tr_progress(self, collection_id, job_id, skip=0, limit=100):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job):
        logger.info(f"job {job.pk} STOPPED, user id:{ job.creator.pk}. Bye!")
        return
    page, loops, progress = remove_collection_from_tr_passages(
        collection_id=collection_id, skip=skip, limit=limit
    )
    logger.info(
        f"job({job.pk}) running for collection={collection_id}"
        f"{page}/{loops} {progress}%"
    )
    update_job_progress(task=self, job=job, progress=progress)

    if progress < 1.0:
        remove_collection_in_tr_progress.delay(
            collection_id=collection_id, job_id=job.pk, skip=skip + limit, limit=limit
        )
    else:
        update_job_completed(task=self, job=job)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_user_registered(self, user_id):
    logger.info(f"user({user_id}) just registered")
    # send confirmation email to the registered user
    # and send email to impresso admins
    send_emails_after_user_registration(user_id=user_id, logger=logger)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_user_activation(self, user_id):
    logger.info(f"user({user_id}) is now active")
    # send confirmation email to the registered user
    # and send email to impresso admins
    send_emails_after_user_activation(user_id=user_id, logger=logger)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def email_password_reset(
    self,
    user_id,
    token="nonce",
    callback_url="https://impresso-project.ch/app/reset-password",
):
    logger.info(f"user({user_id}) requested password reset!")
    # send confirmation email to the registered user
    # and send email to impresso admins
    send_email_password_reset(
        user_id=user_id, token=token, callback_url=callback_url, logger=logger
    ),


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def add_to_collection_from_tr_passages_query(
    self,
    collection_id,
    user_id,
    query,
    content_type="A",
    fq=None,
    serialized_query=None,
    skip=0,
    limit=100,
):
    # check that the collection exists and user has access.
    collection = Collection.objects.get(pk=collection_id, creator__id=user_id)
    # save current job!
    job = Job.objects.create(
        type=Job.BULK_COLLECTION_FROM_QUERY_TR,
        creator=collection.creator,
        status=Job.RUN,
    )
    # add current collection to extra.
    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        extra={
            "collection": get_collection_as_obj(collection),
            "query": query,
            "serializedQuery": serialized_query,
        },
        message=f"Add to collection {collection_id} from tr_passages query {query}",
    )
    # execute premiminary query
    add_to_collection_from_tr_passages_query_progress.delay(
        query=query, job_id=job.pk, collection_id=collection_id, skip=skip, limit=limit
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def add_to_collection_from_tr_passages_query_progress(
    self,
    query,
    job_id,
    collection_id,
    skip=0,
    limit=100,
):
    """
    Add the content item id resulting from given solr search query on tr_passages index to a collection.

    Args:
        query: The query string to execute on tr_passages index.
        job_id: The job id to update.
        collection_id: The collection id to add the content items to.
        skip: The number of results to skip.
        limit: The number of results to return.
        prev_progress: The previous progress value.

    Returns:
        The result of the task.
    """
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job):
        logger.info(f"job {job.pk} STOPPED, user id:{ job.creator.pk}. Bye!")
        return
    page, loops, progress = add_tr_passages_query_results_to_collection(
        collection_id=collection_id,
        query=query,
        skip=skip,
        limit=limit,
        job=job,
    )
    update_job_progress(
        task=self,
        job=job,
        progress=progress,
        message=f"loop {page} of {loops} collection={collection_id}",
    )

    if progress < 1.0:
        # call the task again, updating the skip and limit
        add_to_collection_from_tr_passages_query_progress.delay(
            query=query,
            job_id=job_id,
            collection_id=collection_id,
            skip=skip + limit,
            limit=limit,
        )
    else:
        # save number of item added to collection
        collection = Collection.objects.get(
            pk=collection_id, creator__id=job.creator.pk
        )
        # update collection count_items manually from main index.
        total = collection.update_count_items()
        # done!
        update_job_completed(
            task=self,
            job=job,
            message=f"loop {page} of {loops} collection={collection_id} items={total}",
        )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def update_collection(
    self, collection_id, user_id, items_ids_to_add=[], items_ids_to_remove=[]
):
    # verify that the collection belong to the user
    try:
        Collection.objects.get(pk=collection_id, creator__id=user_id)
    except Collection.DoesNotExist:
        logger.info(f"Collection {collection_id} not found for user {user_id}")
        return

    if items_ids_to_add:
        store_collection.delay(
            collection_id=collection_id,
            items_ids=items_ids_to_add,
            method=METHOD_ADD_TO_INDEX,
        )
    if items_ids_to_remove:
        store_collection.delay(
            collection_id=collection_id,
            items_ids=items_ids_to_remove,
            method=METHOD_DEL_FROM_INDEX,
        )
    # update count items in collection (db)
    count_items_in_collection.delay(collection_id=collection_id)


@app.task(bind=True)
def update_user_bitmap_task(self, user_id):
    """
    Update the user bitmap for the given user.
    """
    logger.info(f"User bitmap update request for user {user_id}")
    updated_bitmap = update_user_bitmap(user_id=user_id)
    return updated_bitmap
