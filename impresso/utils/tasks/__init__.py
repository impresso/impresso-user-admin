import math
import json
from typing import Tuple, Any, Dict, Optional
from django.conf import settings
from ...models import Job


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
    Generic function to update a job that also specify the `task` message
    autoatically get the Impresso Middle Layer.

    Args:
        task (Any): The task object.
        job (Job): The job object.
        progress (float): The current progress of the job.
        taskstate (str, optional): The state of the task. Defaults to TASKSTATE_PROGRESS.
        extra (Dict[str, Any], optional): Additional metadata for the job. Defaults to {}.
        message (str, optional): A message to log. Defaults to "".
        logger (Optional[Any], optional): Logger instance for logging. Defaults to None.
    """
    # this is the JSON message that will be stored in REDIS (celery) and
    # get from src/selery.ts module in Impresso Middle Layer.
    # among the extra: `collection:Dict` and `query:str`.
    try:
        job_current_extra = json.loads(job.extra)
    except json.JSONDecodeError:
        job_current_extra = {}
    except TypeError:
        job_current_extra = {}
    # add or update basic task info
    job_current_extra.update(
        {
            "channel": job.creator.profile.uid,
            "taskname": task.name,
            "taskstate": taskstate,
            "progress": progress,
            "message": message,
        },
        **extra,
    )
    # update the job extra field, it is an old TextField
    job.extra = json.dumps(job_current_extra)
    if logger:
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] "
            f"type={job.type} status={job.status} taskstate={taskstate} "
            f"progress={progress * 100:.2f}% - message: '{message}'"
        )
    job.save()
    task.update_state(
        state=taskstate,
        meta={
            "job": {
                "id": job.pk,
                "type": job.type,
                "status": job.status,
                "date_created": job.date_created.isoformat(),
                "date_last_modified": job.date_last_modified.isoformat(),
                "creator": job.creator.id,
                "description": job.description,
            },
            **job_current_extra,
        },
    )


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
