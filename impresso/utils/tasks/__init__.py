import math
import json
from django.conf import settings
from ...models import Job

TASKSTATE_INIT = "INIT"
TASKSTATE_PROGRESS = "PROGRESS"
TASKSTATE_SUCCESS = "SUCCESS"
TASKSTATE_STOPPED = "STOPPED"


def get_pagination(skip, limit, total, job=None):
    limit = min(limit, settings.IMPRESSO_SOLR_EXEC_LIMIT)
    max_loops = (
        min(
            job.creator.profile.max_loops_allowed, settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
        )
        if job
        else settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
    )
    page = 1 + skip / limit
    # get n of loops allowed
    loops = min(math.ceil(total / limit), max_loops)
    # 100% progress if there's no loops...
    progress = page / loops if loops > 0 else 1.0
    return page, loops, progress, max_loops


def get_list_diff(a, b) -> list:
    return [item for item in a if item not in b] + [item for item in b if item not in a]


def update_job_progress(
    task, job, progress, taskstate=TASKSTATE_PROGRESS, extra={}, message="", logger=None
):
    """
    generic function to update a job
    """
    meta = job.get_task_meta(taskname=task.name, progress=progress, extra=extra)
    if logger:
        logger.info(
            f"[job:{job.pk}, user:{job.creator.pk}] "
            f"type={job.type} status={job.status} taskstate={taskstate} "
            f"progress={progress * 100:.2f}% - message: '{message}'"
        )
    job.extra = json.dumps(meta)
    job.save()
    task.update_state(state=taskstate, meta=meta)


def update_job_completed(task, job, extra={}, message="", logger=None):
    """
    Call update_job_progress for one last time.
    This method sets the job status to Job.DONE
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


def is_task_stopped(task, job, progress=None, extra={}, logger=None):
    """
    Check if a job has been stopped by the user.
    If yes, this methos sets the job status to STOPPED for you,
    then call update_job_progress one last time.
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


def mapper_doc_redact_contents(doc):
    doc_year = int(doc["year"])
    # @todo to be changed according to user settings
    if "is_content_available" in doc:
        if doc["is_content_available"] != "true":
            doc["content"] = "[redacted]"
            doc["is_content_available"] = ""
        else:
            doc["is_content_available"] = "y"
    elif doc_year >= settings.IMPRESSO_CONTENT_DOWNLOAD_MAX_YEAR:
        doc["content"] = "[redacted]"
    return doc


def mapper_doc_remove_private_collections(doc, job):
    if "collections" in doc:
        # remove collection from the doc if they do not start wirh job creator id
        collections = [
            d
            for d in doc["collections"].split(",")
            if d.startswith(str(job.creator.profile.uid))
        ]
        doc["collections"] = ",".join(collections)
    return doc
