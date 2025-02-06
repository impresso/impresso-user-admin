import csv
import logging
import os
from django.conf import settings
from os.path import basename
from typing import Tuple
from zipfile import ZipFile, ZIP_DEFLATED
from ...models import Job
from ...solr import find_all
from ...utils.tasks import get_pagination
from ...utils.bitmask import BitMask64
from ...utils.solr import (
    mapper_doc_remove_private_collections,
    mapper_doc_redact_contents,
    serialize_solr_doc_content_item_to_plain_dict,
)

default_logger = logging.getLogger(__name__)


def get_results_message(total: int, max_loops: int, limit: int) -> str:
    """
    Generates a message indicating the total number of results and the maximum number of results displayed.

    Args:
      total (int): The total number of results.
      max_loops (int): The maximum number of loops to display results.
      limit (int): The limit of results per loop.

    Returns:
      str: A message indicating the total number of results and the maximum number of results displayed.
    """
    max_displayed = max_loops * limit
    if total <= max_displayed:
        message = f"Total results: {total}."
    else:
        message = (
            f"Total results: {total}. "
            f"Showing a maximum of {max_displayed} results due to display limits."
        )
    return message


def helper_export_query_as_csv_progress(
    job: Job,
    query: str,
    query_hash: str,
    user_bitmap_key: int,
    ignore_fields: list = [],
    skip: int = 0,
    limit: int = 100,
    logger: logging.Logger = default_logger,
) -> Tuple[int, int, float]:
    """
    Helper function to export a SOLR query as a CSV file, with progress tracking.
    The function will write the results of the query to a CSV file, respecting the user's bitmap key.
    The function will also remove private collections from the content items.
    At the end of the job, the function will create a zip file containing the CSV file.

    Args:
      job (Job): The job object containing user profile information.
      query (str): The SOLR query string.
      query_hash (str): The hash of the query string.
      user_bitmap_key (int): The user's bitmap key.
      skip (int, optional): The number of items to skip. Defaults to 0.
      limit (int, optional): The maximum number of items per page. Defaults to 0.
      logger (Any, optional): The logger object. Defaults to None.
    Returns:
      Tuple[int, int, float]: A tuple containing:
        - page (int): The current page number.
        - loops (int): The number of loops allowed.
        - progress (float): The progress percentage.
    """
    # remove fields to speed up the process
    query_param_fl = [
        field
        for field in settings.IMPRESSO_SOLR_FIELDS_AS_LIST
        if field not in ignore_fields
    ]
    contents = find_all(q=query, fl=",".join(query_param_fl), skip=skip, logger=logger)
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

    if total == 0:
        logger.info(f"[job:{job.pk} user:{job.creator.pk}] No results found, aborting.")
        return (
            page,
            loops,
            progress,
        )
    user_bitmask = BitMask64(user_bitmap_key)
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] Opening file in APPEND mode:"
        f"{job.attachment.upload.path}"
    )
    # remove fields starting with _ from the list of fields, see
    # settings.IMPRESSO_SOLR_ARTICLE_PROPS
    fieldnames = [
        field
        for field in settings.IMPRESSO_SOLR_ARTICLE_PROPS
        if not field.startswith("_") and field not in ignore_fields
    ]
    # Sort fieldnames with 'uid' first, then the rest alphabetically
    with open(
        job.attachment.upload.path, mode="a", encoding="utf-8-sig", newline=""
    ) as csvfile:
        w = csv.DictWriter(
            csvfile,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
            fieldnames=fieldnames,
        )

        if page == 1:
            logger.info(
                f"[job:{job.pk} user:{job.creator.pk}] writing header: {fieldnames}"
            )
            # write custom header
            w.writerow({fieldnames[0]: get_results_message(total, max_loops, limit)})
            w.writerow(
                {
                    fieldnames[
                        0
                    ]: f"Explore the list of result: (https://impresso-project.ch/app/search?sq={query_hash})"
                }
            )
            w.writerow(
                {
                    fieldnames[0]: settings.IMPRESSO_CONTENT_DOWNLOAD_DISCLAIMER,
                }
            )
            # empty line
            w.writerow({})
            w.writeheader()

        # filter out docs without proper metadata. We will warn about them in a moment
        rows = [
            doc
            for doc in contents["response"]["docs"]
            if doc.get("meta_journal_s", False)
        ]

        if len(rows) != len(contents["response"]["docs"]):
            logger.warning(
                f"[job:{job.pk} user:{job.creator.pk}] Warning: some docs do not have meta_journal_s field. Check: {[
                    doc.get('id', 'no id??') for doc in contents['response']['docs'] if not doc.get('meta_journal_s', False)
                ]}"
            )

        user_allow_temporarily_no_redaction = job.creator.groups.filter(
            name=settings.IMPRESSO_GROUP_USER_PLAN_NO_REDACTION
        ).exists()
        logger.info(
            f"[job:{job.pk} user:{job.creator.pk}] "
            f"User allow temporarily no redaction: {user_allow_temporarily_no_redaction}"
        )
        for row in rows:
            content_item = serialize_solr_doc_content_item_to_plain_dict(row)
            content_item = mapper_doc_remove_private_collections(
                doc=content_item, prefix=job.creator.profile.uid
            )
            if not user_allow_temporarily_no_redaction:
                content_item = mapper_doc_redact_contents(
                    doc=content_item,
                    user_bitmask=user_bitmask,
                )
            # removed unwanted fields from the content_item
            content_item = {k: v for k, v in content_item.items() if k in fieldnames}
            w.writerow(content_item)
    if page < loops:
        return (
            page,
            loops,
            progress,
        )
    # Job is done, close the file and create the zip
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] "
        f"Job finished, closing file: {job.attachment.upload.path}"
    )
    # create the zip file
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
    return (
        page,
        loops,
        progress,
    )
