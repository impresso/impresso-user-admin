import math
import json
from typing import Tuple, Any, Dict, Optional
from django.conf import settings
from ...models import Job
from ..bitmap import check_bitmap_keys_overlap

TASKSTATE_INIT = "INIT"
TASKSTATE_PROGRESS = "PROGRESS"
TASKSTATE_SUCCESS = "SUCCESS"
TASKSTATE_STOPPED = "STOPPED"


def get_pagination(
    skip: int, limit: int, total: int, job: Job, ignore_max_loops: bool = False
) -> Tuple[int, int, float, int]:
    """
    Calculate pagination details including the current page, number of loops, progress, and maximum loops allowed.

    Args:
        skip (int): The number of items to skip.
        limit (int): The maximum number of items per page.
        total (int): The total number of items.
        job (Optional[Job], optional): The job object containing user profile information. Defaults to None.
        ignore_max_loops (bool, optional): Whether to ignore the maximum number of loops allowed. Defaults to False.
    Returns:
        Tuple[int, int, float, int]: A tuple containing:
            - page (int): The current page number.
            - loops (int): The number of loops allowed.
            - progress (float): The progress percentage.
            - max_loops (int): The maximum number of loops allowed.
    """
    limit = min(limit, settings.IMPRESSO_SOLR_EXEC_LIMIT)
    max_loops = min(
        job.creator.profile.max_loops_allowed, settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
    )

    page = 1 + skip / limit
    # get n of loops allowed
    if ignore_max_loops:
        loops = math.ceil(total / limit)
    else:
        loops = min(math.ceil(total / limit), max_loops)
    # 100% progress if there's no loops...
    progress = page / loops if loops > 0 else 1.0
    return page, loops, progress, max_loops


def get_list_diff(a, b) -> list:
    return [item for item in a if item not in b] + [item for item in b if item not in a]


def update_job_progress(
    task: Any,
    job: Job,
    progress: float,
    taskstate: str = TASKSTATE_PROGRESS,
    extra: Dict[str, Any] = {},
    message: str = "",
    logger: Optional[Any] = None,
) -> None:
    """
    Generic function to update a job.

    Args:
        task (Any): The task object.
        job (Job): The job object.
        progress (float): The current progress of the job.
        taskstate (str, optional): The state of the task. Defaults to TASKSTATE_PROGRESS.
        extra (Dict[str, Any], optional): Additional metadata for the job. Defaults to {}.
        message (str, optional): A message to log. Defaults to "".
        logger (Optional[Any], optional): Logger instance for logging. Defaults to None.
    """
    meta = job.get_task_meta(taskname=task.name, progress=progress, extra=extra)
    if logger:
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] "
            f"type={job.type} status={job.status} taskstate={taskstate} "
            f"progress={progress * 100:.2f}% - message: '{message}'"
        )
    job.extra = json.dumps(meta)
    job.save()
    task.update_state(state=taskstate, meta=meta)


def update_job_completed(
    task, job: Job, extra: dict = {}, message: str = "", logger=None
) -> None:
    """
    Call update_job_progress for one last time.
    This method sets the job status to Job.DONE

    Args:
        task: The task object.
        job (Job): The job object.
        extra (dict, optional): Additional metadata for the job. Defaults to {}.
        message (str, optional): A message to log. Defaults to "".
        logger (optional): Logger instance for logging. Defaults to None.
    """
    job.status = Job.DONE
    update_job_progress(
        task=task,
        job=job,
        taskstate=TASKSTATE_SUCCESS,
        progress=1.0,
        extra=extra,
        message=message,
        logger=logger,
    )


def is_task_stopped(
    task, job: Job, progress: float = None, extra: dict = {}, logger=None
) -> bool:
    """
    Check if a job has been stopped by the user.
    If yes, this method sets the job status to STOPPED for you,
    then calls update_job_progress one last time.

    Args:
        task: The task object.
        job (Job): The job object.
        progress (float, optional): The current progress of the job. Defaults to None.
        extra (dict, optional): Additional metadata for the job. Defaults to {}.
        logger (optional): Logger instance for logging. Defaults to None.

    Returns:
        bool: True if the job was stopped, False otherwise.
    """
    if job.status != Job.STOP:
        return False
    job.status = Job.RIP
    extra.update({"stopped": True})
    if logger is not None:
        logger.info(f"[job {job.pk},user:{ job.creator.pk}] STOPPED. Bye!")
    update_job_progress(
        task=task,
        job=job,
        progress=progress if progress else 0.0,
        taskstate=TASKSTATE_STOPPED,
        extra=extra,
    )
    return True


def mapper_doc_redact_contents(doc: dict, user_bitmap_key: str) -> dict:
    """
    Redacts the content of a document based on its availability and year.

    This function modifies the input document dictionary by redacting its content
    if certain conditions are met. Specifically, it checks the "is_content_available"
    field and the document's year to determine if the content should be redacted.

    Args:
        doc (dict): A dictionary representing the document. It must contain the keys
                    "year" and optionally "is_content_available".

    Returns:
        dict: The modified document dictionary with redacted content if applicable.

    Notes:
        - If "is_content_available" is present and not equal to "true", the content
          is redacted and "is_content_available" is set to an empty string.
        - If "is_content_available" is "true", it is changed to "y".
        - If the document's year is greater than or equal to the maximum allowed year
          defined in settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR, the content is redacted.
    """
    try:
        doc_year = int(doc["year"])
    except KeyError:
        print(doc)
        raise ValueError("Document does not contain a 'year' field.")

    if doc.get("_bitmap_get_tr", None) is not None:
        if not check_bitmap_keys_overlap(user_bitmap_key, doc["_bitmap_get_tr"]):
            doc["content"] = "[redacted]"
            doc["excerpt"] = "[redacted]"
            doc["is_content_available"] = "N"
        else:
            doc["is_content_available"] = "y"
    elif "is_content_available" in doc:
        if doc["is_content_available"] != "true":
            doc["content"] = "[redacted]"
            doc["is_content_available"] = "N"
        else:
            doc["is_content_available"] = "y"
    elif doc_year >= settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR:
        doc["content"] = "[redacted]"
        doc["is_content_available"] = "N"
    return doc


def mapper_doc_remove_private_collections(doc: dict, job: Job) -> dict:
    """
    Removes the private collections from the document that do not start with the job creator's ID.

    Args:
        doc (dict): The document dictionary containing collections.
        job (Job): The job object containing the creator's profile information.

    Returns:
        dict: The updated document dictionary with filtered collections.
    """
    if "collections" in doc:
        # remove collection from the doc if they do not start wirh job creator id
        collections = [
            d
            for d in doc["collections"].split(",")
            if d.startswith(str(job.creator.profile.uid))
        ]
        doc["collections"] = ",".join(collections)
    return doc
