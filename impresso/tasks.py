from __future__ import absolute_import

import time
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User, Group
from .celery import app
from celery import shared_task, chain
from .models import Job, Collection, CollectableItem, SearchQuery, Attachment
from .models import UserBitmap
from .models import UserChangePlanRequest
from .utils.tasks import (
    TASKSTATE_INIT,
    update_job_progress,
    update_job_completed,
    is_task_stopped,
)
from .utils.tasks.collection import helper_update_collections_in_tr_passages_progress
from .utils.tasks.textreuse import remove_collection_from_tr_passages
from .utils.tasks.textreuse import add_tr_passages_query_results_to_collection
from .utils.tasks.collection import (
    helper_remove_collection_progress,
    helper_store_collection_progress,
)
from .utils.tasks.collection import METHOD_ADD_TO_INDEX, METHOD_DEL_FROM_INDEX
from .utils.tasks.account import (
    send_emails_after_user_registration,
    send_emails_after_user_activation,
    send_email_password_reset,
    send_email_plan_change,
    send_email_plan_change_accepted,
    send_email_plan_change_rejected,
)
from .utils.tasks.userBitmap import helper_update_user_bitmap
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
    logger.info(f"Echo: {message}")
    response = f"Hello world. This is your message: {message}"
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
    user_bitmap_key: int,
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
        user_bitmap_key (int): The user bitmap key, as int.
        query_hash (str, optional): The hash of the query. Defaults to an empty string.
        skip (int, optional): The number of records to skip. Defaults to 0.
        limit (int, optional): The maximum number of records to retrieve per page. Defaults to 100.

    Returns:
        None
    """
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job, progress=progress, logger=logger):
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
        update_job_progress(task=self, job=job, progress=progress, logger=logger)
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
        update_job_completed(task=self, job=job, logger=logger)


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
    attachment = Attachment.create_from_job(job, extension="csv")
    # if decri
    # get user bitmap, if any
    user_bitmap, created = UserBitmap.objects.get_or_create(user_id=user_id)
    logger.info(
        f"[job:{job.pk} user:{user_id}] launched! "
        f"- Using bitmap {user_bitmap.get_bitmap_as_int()} (created:{created}) "
        f"- attachment:{attachment.pk}"
    )

    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        logger=logger,
        extra={"query": query, "query_hash": query_hash},
    )

    export_query_as_csv_progress.delay(
        job_id=job.pk,
        query=query,
        query_hash=query_hash,
        search_query_id=search_query_id,
        user_bitmap_key=user_bitmap.get_bitmap_as_int(),
    )


@app.task(bind=True)
def export_collection_as_csv(
    self,
    user_id: int,
    collection_id: int,
    query: str,
    query_hash: str = "",
) -> None:
    """
    Initiates a job to export a collection as a CSV file and starts the export_query_as_csv_progress task
    like export_query_as_csv.

    Args:
        self: The instance of the class.
        user_id (int): The ID of the user initiating the export.
        collection_id (int): The ID of the collection to be exported.
        query (str): The query string to be exported.
        query_hash (str, optional): A hash of the query string. Defaults to an empty string.

    Returns:
        None

    """
    user_bitmap, created = UserBitmap.objects.get_or_create(user_id=user_id)
    try:
        collection = Collection.objects.get(pk=collection_id, creator__id=user_id)
    except Collection.DoesNotExist:
        logger.error(f"[job:{job.pk} user:{user_id}] no collection found for user!")
        return
    # save current job then start export_query_as_csv task.
    job = Job.objects.create(
        type=Job.EXPORT_QUERY_AS_CSV,
        creator_id=user_id,
        description=collection.name,
        extra={
            "collection": get_collection_as_obj(collection),
            "query": query,
            "query_hash": query_hash,
        },
    )
    # create empty attachment and attach automatically to the job
    attachment = Attachment.create_from_job(job, extension="csv")
    logger.info(
        f"[job:{job.pk} user:{user_id}] launched! "
        f"- Using bitmap {user_bitmap.get_bitmap_as_int()} (created:{created}) "
        f"- attachment:{attachment.pk} "
        f"- query:{query_hash} description:{job.description}"
    )

    # add query to extra. Job status should be INIT
    update_job_progress(
        task=self,
        job=job,
        taskstate=TASKSTATE_INIT,
        progress=0.0,
        logger=logger,
    )

    export_query_as_csv_progress.delay(
        job_id=job.pk,
        query=query,
        query_hash=query_hash,
        user_bitmap_key=user_bitmap.get_bitmap_as_int(),
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def store_collection_progress(
    self,
    job_id: int,
    collection_id: int,
    items_ids: list[int],
    skip: int,
    limit: int,
    progress: float = 0.0,
    content_type: str = "A",
    method: str = METHOD_ADD_TO_INDEX,
) -> None:
    """
    Store the progress of a collection processing job.

    This function updates the progress of a job that processes a collection of items.
    It constructs a query based on the provided item IDs and synchronizes the query
    results to the collection. If the collection is marked as deleted, it logs the
    status and updates the job as completed. Otherwise, it continues to update the
    job progress and recursively calls itself until the processing is complete.

    Args:
        self: The task instance.
        job_id (int): The ID of the job.
        collection_id (int): The ID of the collection.
        items_ids (list[int]): A list of item IDs to be processed.
        skip (int): The number of items to skip in the query.
        limit (int): The maximum number of items to process in one batch.
        content_type (str): The type of content being processed.
        method (str): The method used for processing.

    Returns:
        None
    """

    job = Job.objects.get(pk=job_id)
    try:
        collection = Collection.objects.get(pk=collection_id)
    except Collection.DoesNotExist:
        logger.warning(f"Collection.DoesNotExist in DB with pk={collection_id}, skip.")
        update_job_completed(
            task=self,
            job=job,
            extra=extra,
            logger=logger,
            message="Collection doesn't exist!",
        )
        return

    if collection.status == Collection.DELETED:
        logger.info(f"Collection {collection_id} status is DEL, exit!")
        extra.update({"cleared": True, "reason": "Collection has status:DEL"})
        update_job_completed(
            task=self,
            job=job,
            extra=extra,
            logger=logger,
            message="Collection is marked for deletion!",
        )
        return

    if is_task_stopped(task=self, job=job, progress=progress, logger=logger):
        count_items_in_collection.delay(collection_id=collection_id)
        update_collections_in_tr_passages.delay(
            collection_prefix=collection_id, user_id=collection.creator.pk
        )
        return

    query = " OR ".join(map(lambda id: f"id:{id}", items_ids))
    extra = {
        "collection_id": collection_id,
        "collection": get_collection_as_obj(collection),
        "items_ids": items_ids,
        "query": query,
        "method": method,
    }

    page, loops, progress = helper_store_collection_progress(
        job=job,
        collection_id=collection_id,
        query=query,
        content_type=content_type,
        method=method,
        skip=skip,
        limit=limit,
        logger=logger,
    )
    if page < loops:
        job.status = Job.RUN
        update_job_progress(
            task=self, job=job, progress=progress, extra=extra, logger=logger
        )
        store_collection_progress.delay(
            job_id=job.pk,
            collection_id=collection_id,
            items_ids=items_ids,
            skip=page * limit,
            limit=limit,
            progress=progress,
            content_type=content_type,
            method=method,
        )
    else:
        update_job_completed(task=self, job=job, extra=extra, logger=logger)
        count_items_in_collection.delay(collection_id=collection_id)
        update_collections_in_tr_passages.delay(
            collection_prefix=collection_id, user_id=collection.creator.pk
        )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def store_collection(
    self,
    collection_id: int,
    items_ids: list = [],
    method: str = METHOD_ADD_TO_INDEX,
    content_type: str = "A",
) -> None:
    """
    Add items_ids to an existing collection.

    Args:
        self: The task instance.
        collection_id (int): The ID of the collection to update.
        items_ids (list, optional): The list of item IDs to add or remove. Defaults to an empty list.
        method (str, optional): The method to use for updating the collection. Defaults to METHOD_ADD_TO_INDEX.
        content_type (str, optional): The content type of the items. Defaults to "A".

    Returns:
        None
    """

    # @todo check if the collection is not deleted
    try:
        collection = Collection.objects.get(pk=collection_id)
        if collection.status == Collection.DELETED:
            logger.info(
                f"Collection found with pk={collection_id}, "
                f"status={collection_to_update}"
            )
        collection_to_update = collection.status != Collection.DELETED
        logger.info(
            f"Collection found with pk={collection_id}, "
            f"status={collection_to_update}"
        )
    except Collection.DoesNotExist:
        logger.warning(f"Collection.DoesNotExist in DB with pk={collection_id}, skip.")
        return

    if method == METHOD_DEL_FROM_INDEX:
        job_type = Job.REMOVE_FROM_SOLR
    else:
        job_type = Job.SYNC_COLLECTION_TO_SOLR
    job = Job.objects.create(type=job_type, creator=collection.creator, status=Job.RUN)

    logger.info(
        f"[job:{job.pk} user:{collection.creator.pk}] started for collection:{collection.pk}!"
    )
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
        logger=logger,
    )
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
    progress=0.0,
    serialized_query=None,
):
    job = Job.objects.get(pk=job_id)
    if is_task_stopped(task=self, job=job, progress=progress, logger=logger):
        return

    # get the collection so that we can see its status
    try:
        collection = Collection.objects.get(pk=collection_id)
    except Collection.DoesNotExist:
        update_job_completed(
            task=self,
            job=job,
            extra={
                "collection": {"pk": collection_id},
                "query": query,
                "serializedQuery": serialized_query,
            },
            message=f"Collection doesn't exist tith pk={collection_id}",
            logger=logger,
        )
        return
    if collection.status == Collection.DELETED:
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
            message="Collection is marked for deletion...",
            logger=logger,
        )
        return
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] "
        f"Collection {collection_id}(status:{collection.status})"
        f"saving query hash = {serialized_query}"
    )
    page, loops, progress = helper_store_collection_progress(
        job=job,
        collection_id=collection_id,
        query=query,
        content_type=content_type,
        skip=skip,
        limit=limit,
        logger=logger,
    )

    if page < loops:
        job.status = Job.RUN
        update_job_progress(task=self, job=job, progress=progress, logger=logger)

        add_to_collection_from_query_progress.delay(
            query=query,
            fq=fq,
            job_id=job_id,
            collection_id=collection_id,
            content_type=content_type,
            skip=skip + limit,
            limit=limit,
            serialized_query=serialized_query,
            progress=progress,
        )
    else:
        count_items_in_collection.delay(collection_id=collection_id)
        update_collections_in_tr_passages.delay(
            collection_prefix=collection_id, user_id=collection.creator.pk
        )
        update_job_completed(task=self, job=job, logger=logger)


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
    page, loops, progress = helper_remove_collection_progress(
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
    page, loops, progress = helper_update_collections_in_tr_passages_progress(
        collection_id=collection_prefix, job=job, skip=skip, limit=limit, logger=logger
    )

    update_job_progress(task=self, job=job, progress=progress, extra=extra)

    if page < loops:
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
    logger.info(f"[user:{user_id}] just registered")
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
    logger.info(f"[user:{user_id}] is now active")
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
    logger.info(f"[user:{user_id}] requested password reset!")
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
def email_plan_change(self, user_id: int, plan: str = None) -> None:
    """
    Sends an email notification for a user's plan change request.

    Args:
        self: The task instance.
        user_id (int): The ID of the user requesting the plan change.
        plan (str, optional): The new plan requested by the user. Defaults to None.

    Returns:
        None
    """
    logger.info(f"[user:{user_id}] requested plan change to {plan}!")
    # send confirmation email to the registered user
    # and send email to impresso admins
    send_email_plan_change(user_id=user_id, plan=plan, logger=logger)


@app.task(bind=True)
def add_user_to_group_task(self, user_id: int, group_name: str) -> int:
    """
    Task to add a user to a group.

    Args:
        user_id (int): The ID of the user to be added to the group.
        group_name (str): The name of the group to which the user will be added.

    Returns:
        int: The ID of the user after being added to the group.
    """
    logger.info(f"[user:{user_id}] adding user to group {group_name}")
    user = User.objects.get(id=user_id)
    group = Group.objects.get(name=group_name)
    user.groups.add(group)


@app.task(bind=True)
def remove_user_from_group_task(self, user_id: int, group_name: str) -> int:
    """
    Task to remove a user from a group.

    Args:
        user_id (int): The ID of the user to be removed from the group.
        group_name (str): The name of the group from which the user will be removed.

    Returns:
        int: The ID of the user after being removed from the group.
    """
    logger.info(f"[user:{user_id}] removing user from group {group_name}")
    user = User.objects.get(id=user_id)
    group = Group.objects.get(name=group_name)
    user.groups.remove(group)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def email_change_plan_request_accepted(self, user_id: int, plan: str = None) -> None:
    logger.info(f"[user:{user_id}] sending email after plan change ACCEPTED")
    send_email_plan_change_accepted(user_id=user_id, plan=plan, logger=logger)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def email_change_plan_request_rejected(self, user_id: int, plan: str = None) -> None:
    logger.info(f"[user:{user_id}] sending email after plan change REJECTED")
    send_email_plan_change_rejected(user_id=user_id, plan=plan, logger=logger)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_change_plan_request_updated(self, user_id: int) -> None:
    """
    Accepts user request (if it is not rejected!) then
    sends an email notification for an accepted plan change request.

    Args:
        self: The task instance.
        user_id (int): The ID of the user requesting the plan change.

    Returns:
        None
    """
    # get request
    try:
        req = UserChangePlanRequest.objects.get(user_id=user_id)
    except UserChangePlanRequest.DoesNotExist:
        logger.error(f"[user:{user_id}] UserChangePlanRequest.DoesNotExist")
        return
    logger.info(f"[user:{user_id}] plan change to {req.plan.name} status {req.status}")

    if req.status == UserChangePlanRequest.STATUS_APPROVED:
        chain(
            add_user_to_group_task.si(user_id, req.plan.name),
            email_change_plan_request_accepted.si(user_id, req.plan.name),
        )()
    elif req.status == UserChangePlanRequest.STATUS_REJECTED:
        chain(
            remove_user_from_group_task.si(user_id, req.plan.name),
            email_change_plan_request_rejected.si(user_id, req.plan.name),
        )()


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_plan_change_rejected(self, user_id: int) -> None:
    """
    Rejects user request (if it is not already accepted!) then
    sends an email notification for a rejected plan change request.

    Args:
        self: The task instance.
        user_id (int): The ID of the user requesting the plan change.

    Returns:
        None
    """
    # get request
    try:
        req = UserChangePlanRequest.objects.get(user_id=user_id)
    except UserChangePlanRequest.DoesNotExist:
        logger.error(f"UserChangePlanRequest.DoesNotExist for user {user_id}")
        return
    # if request is not PENDING, send out an error email.
    if req.status == UserChangePlanRequest.STATUS_APPROVED:
        logger.error(
            f"[user:{user_id}] plan change to {req.plan.name} is APPROVED, can't reject. Change the status in the DB before !"
        )
    logger.info(
        f"[user:{user_id}] request to change plan to {req.plan.name} has been REJECTED!"
    )
    # save Rejected status to the plan request
    req.status = UserChangePlanRequest.STATUS_REJECTED
    req.save()
    # send confirmation email to the registered user
    send_email_plan_change_rejected(user_id=user_id, plan=req.plan.name, logger=logger)


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
    # save current job!
    job = Job.objects.create(
        type=Job.UPDATE_USER_BITMAP, creator_id=user_id, status=Job.RUN
    )
    serialized_userBitmap = helper_update_user_bitmap(user_id=user_id)
    # done!
    update_job_completed(
        task=self,
        job=job,
        message="User bitmap updated!",
        extra={"userBitmap": serialized_userBitmap},
    )
    return serialized_userBitmap
