import logging
from typing import Tuple
from django.conf import settings
from django.db.utils import IntegrityError
from . import get_pagination
from ...solr import find_all, update
from ...models import Collection, CollectableItem, Job

default_logger = logging.getLogger(__name__)


def get_indexed_tr_passages_by_items(
    items_ids, limit, skip, job, logger
):
    """
    Searches for indexed passages for a given list of item IDs using the Solr search engine.

    Args:
        items_ids: A list of content item IDs to search for in tr_passages ci_id_s property.
        limit: The maximum number of passages to return (default=10).
        skip: The number of passages to skip before starting to return results (default=0).
        total: the total number of passages found for the given query.
        logger: A logger object to log information during the execution of the function (default=default_logger).

    Returns:
        A tuple containing the current page, number of loops, progress, total number of results,
        and the actual search results in the form of a list of dictionaries.
    """
    query = " OR ".join(f"ci_id_s:{item_id}" for item_id in items_ids)
    res = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT,
        fl="id,ucoll_ss,_version_,ci_id_s",
        limit=limit,
        skip=skip,
        sort="id asc",
    )
    total = res["response"]["numFound"]
    # we don't use the get_pagination `Job` object here not to limit loops. See settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
    page, loops, progress, _max_loops = get_pagination(skip=skip, limit=limit, total=total, job=job)
    logger.info(
        f"SUCCESS numFound={total} page={page} loops={loops} progress={progress}"
    )
    return (page, loops, progress, total, res["response"]["docs"])


def remove_collection_from_tr_passages(
    collection_id: str,
    job: Job,
    skip: int = 0,
    limit: int = 100,
    logger: logging.Logger = default_logger,
) -> Tuple[int, int, float]:
    """
    Remove a collection from text reuse passages in the Solr index.

    Args:
        collection_id (str): The ID of the collection to be removed.
        skip (int, optional): The number of initial records to skip. Defaults to 0.
        limit (int, optional): The maximum number of records to process in one batch. Defaults to 100.
        logger (Logger, optional): Logger instance for logging information. Defaults to default_logger.

    Returns:
        tuple: A tuple containing:
            - page (int): The current page number.
            - loops (int): The number of loops required to process all records.
            - progress (float): The progress percentage of the operation.
    """

    query = f"ucoll_ss:{collection_id}"
    # 1. get text reuse passages matching collection_id
    tr_passages_request = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT,
        fl="id,ucoll_ss,_version_,ci_id_s",
        skip=0,
        limit=limit,
        logger=logger,
    )
    total = tr_passages_request["response"]["numFound"]
    qtime = tr_passages_request["responseHeader"]["QTime"]
    page, loops, progress, max_loops = get_pagination(
        skip=0, limit=limit, total=total, job=job, ignore_max_loops=True
    )
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] "
        f" query = {query} -"
        f" total:{total} in {qtime}ms -"
        f" loops:{loops} - max_loops:{max_loops} -"
        f" page:{page} - progress:{progress} -"
    )
    # 2. get update objects for text reuse index.
    solr_tr_passages = tr_passages_request.get("response", {}).get("docs", [])
    solr_updates_needed = []
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] " f"{tr_passages_request['response']}"
    )
    for doc in solr_tr_passages:
        # get list of collection in ucoll_ss field
        ucoll_list = doc.get("ucoll_ss", [])
        logger.info(ucoll_list)
        if collection_id not in ucoll_list:
            continue
        ucoll_list.remove(collection_id)
        solr_updates_needed.append(
            {
                "id": doc.get("id"),
                "_version_": doc.get("_version_"),
                "ucoll_ss": {"set": ucoll_list},
            }
        )
    logger.info(
        f"[job:{job.pk} user:{job.creator.pk}] "
        f"n. Solr updates needed in text_reuse: {len(solr_updates_needed)}"
    )
    # more than one
    if solr_updates_needed:
        result = update(
            url=settings.IMPRESSO_SOLR_PASSAGES_URL_UPDATE,
            todos=solr_updates_needed,
            logger=logger,
        )
        result_response_header = result.get("responseHeader")
        result_adds = len(result.get("adds", []))
        logger.info(
            f"(update) solr updates response={result_response_header}, "
            f"adds={result_adds}"
        )
    # save all items there!
    return (page, loops, progress)


def add_tr_passages_query_results_to_collection(
    collection_id: str,
    job: Job,
    query: str,
    skip: int = 0,
    limit: int = 100,
    logger: logging.Logger = default_logger,
) -> Tuple[int, int, float]:
    """
    Set collection_id in ucoll_ss field of text reuse passages matching query.
    Firstly we set the collection_id in the article solr index, and we add the collection to tr passages in a second time.

    Args:
        collection_id (str): The ID of the collection to be added.
        query (str): The query to match text reuse passages.
        skip (int, optional): The number of initial records to skip. Defaults to 0.
        limit (int, optional): The maximum number of records to process in one batch. Defaults to 100.
        logger (Logger, optional): Logger instance for logging information. Defaults to default_logger.
        job (Job, optional): Job instance to limit the number of loops. Defaults to None.

    Returns:
        Tuple[int, int, float]: A tuple containing:
            - page (int): The current page number.
            - loops (int): The number of loops required to process all records.
            - progress (float): The progress percentage of the operation.
    """
    collection = Collection.objects.get(pk=collection_id)
    logger.info(
        f"ucoll_ss={collection_id} " f"query={query} collection name={collection.name})"
    )

    content_items = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT,
        fl="id,ci_id_s,ucoll_ss,_version_,score",
        skip=skip,
        limit=limit,
        sort="score DESC,id ASC",
        fq="{!collapse field=ci_id_s}",
        logger=logger,
    )
    total_content_items = content_items["response"]["numFound"]
    # if Job is not none, we limit the number of loops to the value of job.creator.profile.max_allowed_loops
    page, loops, progress, max_loops = get_pagination(
        skip=skip, limit=limit, total=total_content_items, job=job
    )
    solr_content_items = content_items.get("response", {}).get("docs", [])
    logger.info(
        f"SOLR find_all success, numFound={total_content_items} "
        f"max_loops={max_loops} page={page} loops={loops}"
        f"skip={skip} limit={limit} ({progress * 100}% compl.)"
    )
    try:
        CollectableItem.objects.bulk_create(
            map(
                lambda doc: CollectableItem(
                    item_id=doc.get("ci_id_s"),
                    content_type=CollectableItem.ARTICLE,
                    collection_id=collection_id,
                    search_query_score=doc.get("score"),
                ),
                solr_content_items,
            ),
            ignore_conflicts=True,
        )
    except IntegrityError as e:
        logger.exception(e)
    else:
        logger.info(
            f"DB bulk_create success, {total_content_items} items assigned to collection {collection.pk} "
        )
    items_ids = [doc.get("ci_id_s", None) for doc in solr_content_items]
    # add collection to articles. fast.
    collection.add_items_to_index(
        items_ids=items_ids,
        solr_url_select=settings.IMPRESSO_SOLR_URL_SELECT,
        solr_url_update=settings.IMPRESSO_SOLR_URL_UPDATE,
        solr_auth_select=settings.IMPRESSO_SOLR_AUTH,
        solr_auth_update=settings.IMPRESSO_SOLR_AUTH_WRITE,
    )
    # add collection to tr passages
    # Now lets add the collection to the tr passages
    tr_page = 0
    tr_loops = 1
    # loop till we have all the tr passages
    while tr_page < tr_loops:
        (
            tr_page,
            tr_loops,
            tr_progress,
            total_tr_passages,
            tr_passages,
        ) = get_indexed_tr_passages_by_items(
            items_ids=items_ids,
            limit=limit,
            skip=tr_page * limit,
            job=job,
            logger=logger,
        )

        logger.info(
            f"SOLR tr_passages find_all success, numFound={total_tr_passages} "
            f"page {tr_page} of {tr_loops} ({tr_progress * 100}% compl.)"
        )
        print([doc.get("id", None) for doc in tr_passages])
        # add escaper for the identifiers in solr:
        # https://lucene.apache.org/solr/guide/7_7/common-query-parameters.html#CommonQueryParameters-Theq%2Ffq%2Ffl%2Fsort%2FetcParameters
        # https://lucene.apache.org/solr/guide/7_7/escaping-characters.html#EscapingCharacters-EscapeSequences
        escaped_ids = [
            doc.get("id", None).replace(":", "\\:").replace("/", "\\/")
            for doc in tr_passages
        ]
        collection.add_items_to_index(
            items_ids=escaped_ids,
            lookup_field="id",
            solr_url_select=settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT,
            solr_url_update=settings.IMPRESSO_SOLR_PASSAGES_URL_UPDATE,
            solr_auth_select=settings.IMPRESSO_SOLR_AUTH,
            solr_auth_update=settings.IMPRESSO_SOLR_AUTH_WRITE,
        )

    logger.info(
        f"ucoll_ss={collection.pk} "
        f"skip={skip} limit={limit} ({progress * 100}% compl.)"
    )
    return (page, loops, progress)
