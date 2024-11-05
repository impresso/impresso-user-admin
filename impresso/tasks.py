from __future__ import absolute_import


import time


from django.conf import settings
from django.contrib.auth.models import User

from .celery import app
from .models import Job, Collection, CollectableItem, SearchQuery, Attachment
from .models import UserBitmap
from .solr import find_all, solr_doc_to_content_item

from celery.utils.log import get_task_logger


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
from .utils.tasks.export import helper_export_query_as_csv_progress

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
def test(self, user_id: int, sleep: int = 1, pace: float = 0.05):
    """
    Initiates a test job and starts the test_progress task.

    Args:
        self: The instance of the class.
        user_id (int): The ID of the user initiating the test.
        sleep (int, optional): The sleep duration between progress updates. Defaults to 1.
        pace (float, optional): The pace of progress updates. Defaults to 0.05.

    Returns:
        None
    """
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
    self,
    job_id: int,
    query: str,
    search_query_id: int,
    user_bitmap_key: str,
    query_hash: str = "",
    progress: float = 0.0,
    skip: int = 0,
    limit: int = 100,
) -> None:
    """
    Export query results as a CSV file with progress tracking.

    This task retrieves query results, writes them to a CSV file, and updates the job's progress.
    If the query has multiple pages of results, the task will recursively call itself to process
    the next page. Once all pages are processed, the CSV file is compressed into a ZIP file.

    Args:
        self: The task instance.
        job_id (int): The ID of the job to update.
        query (str): The query string to execute.
        search_query_id (int): The ID of the search query.
        user_bitmap_key (str): The user bitmap key.
        query_hash (str, optional): The hash of the query. Defaults to an empty string.
        skip (int, optional): The number of records to skip. Defaults to 0.
        limit (int, optional): The maximum number of records to retrieve per page. Defaults to 100.

    Returns:
        None
    """
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    extra = {
        "query": query_hash,
        "search_query_id": search_query_id,
    }
    if is_task_stopped(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    ):
        return

    page, loops, progress = helper_export_query_as_csv_progress(
        job=job,
        query=query,
        query_hash=query_hash,
        user_bitmap_key=user_bitmap_key,
        skip=skip,
        limit=limit,
        logger=logger,
    )

    if page < loops:
        job.status = Job.RUN
        update_job_progress(
            task=self, job=job, progress=progress, extra=extra, logger=logger
        )
        export_query_as_csv_progress.delay(
            job_id=job.pk,
            query=query,
            query_hash=query_hash,
            search_query_id=search_query_id,
            user_bitmap_key=user_bitmap_key,
            skip=page * limit,
            limit=limit,
        )
    else:
        update_job_completed(task=self, job=job, extra=extra, logger=logger)


@app.task(bind=True)
def export_query_as_csv(
    self,
    user_id: int,
    query: str,
    description: str = "",
    query_hash: str = "",
    search_query_id: int = None,
) -> None:
    """
    Initiates a job to export a query as a CSV file and starts the export_query_as_csv_progress task.

    Args:
        self: The instance of the class.
        user_id (int): The ID of the user initiating the export.
        query (str): The query string to be exported.
        description (str, optional): A description for the job. Defaults to an empty string.
        query_hash (str, optional): A hash of the query string. Defaults to an empty string.
        search_query_id (int, optional): The ID of the search query. Defaults to None.

    Returns:
        None
    """
    # save current job then start export_query_as_csv task.
    job = Job.objects.create(
        type=Job.EXPORT_QUERY_AS_CSV,
        creator_id=user_id,
        description=description,
    )

    # get user bitmap, if any
    try:
        print(job.creator.bitmap)
        user_bitmap_key = job.creator.bitmap.get_bitmap_as_key_str()[:2]
    except User.bitmap.RelatedObjectDoesNotExist:
        print(job.creator.bitmap)
        logger.info(f"[job:{job.pk} user:{user_id}] no bitmap found for user!")
        user_bitmap_key = bin(UserBitmap.USER_PLAN_GUEST)[:2]
    logger.info(
        f"[job:{job.pk} user:{user_id}] launched! "
        f"query:{query_hash} bitmap:{user_bitmap_key}"
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
        f"[job:{job.pk} user:{user_id}] started!"
        f" search_query_id:{search_query_id} created:{created}, attachment:{attachment.upload.path}"
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
        logger=logger,
    )

    export_query_as_csv_progress.delay(
        job_id=job.pk,
        query=query,
        query_hash=query_hash,
        search_query_id=search_query_id,
        user_bitmap_key=user_bitmap_key,
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
        task=self,
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
        is_collection_to_delete = (
            collection.status == Collection.DELETED and collection.creator.pk == user_id
        )
        collection_seralized = get_collection_as_obj(collection)
        logger.info(
            f"[job:{job.pk} user:{user_id}]"
            f" Collection found with pk={collection_id},"
            f" status={is_collection_to_delete}"
        )
    except Collection.DoesNotExist:
        collection_seralized = {"pk": collection_id}
        is_collection_to_delete = True
        logger.info(
            f"[job:{job.pk} user:{user_id}] "
            f"Collection.DoesNotExist in DB with pk={collection_id}, removing on SOLR..."
        )
    if not is_collection_to_delete:
        logger.info(
            f"[job:{job.pk} user:{user_id}] "
            f"Cannot delete collection pk={collection_id}, please set it status=DEL!"
        )
        update_job_completed(task=self, job=job, logger=logger)
        return
    # stat loop
    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        extra={"collection": collection_seralized},
        logger=logger,
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
    job_id: int,
    collection_id: int,
    user_id: int,
    limit: int = 100,
    progress: float = 0.0,
) -> None:
    """
    This task attempts to remove a collection in a paginated manner, updating the job progress
    accordingly. If the task is stopped, it will return early. Otherwise, it will continue to
    delete the collection in chunks, updating the progress and retrying if necessary until the
    collection is fully removed.

    Args:
        self (Task): The current task instance.
        job_id (int): The ID of the job associated with this task.
        collection_id (int): The ID of the collection to be removed.
        user_id (int): The ID of the user requesting the removal.
        limit (int, optional): The maximum number of items to process in one go. Defaults to 100.
        progress (float, optional): The current progress of the task. Defaults to 0.0.

    Returns:
        None
    """
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job, progress=progress, logger=logger):
        return
    page, loops, progress = delete_collection(
        collection_id=collection_id, limit=limit, job=job
    )
    update_job_progress(task=self, job=job, progress=progress, extra={}, logger=logger)

    if progress < 1.0:
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
    self,
    job_id: int,
    collection_prefix: str,
    progress: float = 0.0,
    skip: int = 0,
    limit: int = 100,
):
    """
    Updates the progress of collections in TR passages for a given job.
    This function retrieves the job by its ID, checks if the task should be stopped,
    synchronizes the collections in TR passages, updates the job progress, and
    recursively calls itself if the job is not yet complete.
    Args:
        self: The task instance.
        job_id (int): The ID of the job to update.
        collection_prefix (str): The prefix of the collection to update.
        progress (float, optional): The current progress of the job. Defaults to 0.0.
        skip (int, optional): The number of items to skip. Defaults to 0.
        limit (int, optional): The maximum number of items to process in one call. Defaults to 100.
    Returns:
        None
    """
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    extra = {}
    if is_task_stopped(task=self, job=job, progress=progress, extra=extra):
        return
    page, loops, progress = sync_collections_in_tr_passages(
        collection_id=collection_prefix, job=job, skip=skip, limit=limit, logger=logger
    )

    update_job_progress(task=self, job=job, progress=progress, extra=extra)

    if progress < 1.0:
        logger.info(f"[job:{job.pk} user:{job.creator.pk}] task still running!")
        update_collections_in_tr_passages_progress.delay(
            job_id=job_id,
            collection_prefix=collection_prefix,
            progress=progress,
            skip=skip + limit,
            limit=limit,
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
    if is_task_stopped(task=self, job=job, logger=logger):
        return
    page, loops, progress = remove_collection_from_tr_passages(
        collection_id=collection_id, job=job, skip=skip, limit=limit, logger=logger
    )
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] running for collection={collection_id}"
        f"{page}/{loops} {progress}%"
    )
    update_job_progress(task=self, job=job, progress=progress, logger=logger)

    if progress < 1.0:
        remove_collection_in_tr_progress.delay(
            collection_id=collection_id, job_id=job.pk, skip=skip + limit, limit=limit
        )
    else:
        update_job_completed(task=self, job=job, logger=logger)


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
    query: str,
    job_id: int,
    collection_id: str,
    skip: int = 0,
    limit: int = 100,
) -> None:
    """
    Add the content item id resulting from given solr search query on tr_passages index to a collection.

    Args:
        query: The query string to execute on tr_passages index.
        job_id: The job id to update.
        collection_id: The collection id to add the content items to.
        skip: The number of results to skip.
        limit: The number of results to return.
        prev_progress: The previous progress value.
    """
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job):
        return
    page, loops, progress = add_tr_passages_query_results_to_collection(
        collection_id=collection_id,
        job=job,
        query=query,
        skip=skip,
        limit=limit,
        logger=logger,
    )
    update_job_progress(
        task=self,
        job=job,
        progress=progress,
        message=f"loop {page} of {loops} collection={collection_id}",
        logger=logger,
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
