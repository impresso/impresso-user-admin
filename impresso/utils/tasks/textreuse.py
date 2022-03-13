import logging
from django.conf import settings
from . import get_pagination
from ...solr import find_all, update


default_logger = logging.getLogger(__name__)


def remove_collection_from_tr_passages(
    collection_id, skip=0, limit=100,
    logger=default_logger
) -> (int, int, float):
    query = f'ucoll_ss:{collection_id}'
    # 1. get text reuse passages matching collection_id
    tr_passages_request = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT,
        fl='id,ucoll_ss,_version_,ci_id_s',
        skip=skip,
        limit=limit,
        logger=logger)
    total = tr_passages_request['response']['numFound']
    page, loops, progress = get_pagination(skip=0, limit=limit, total=total)
    logger.info(
        f'q={query} numFound={total} '
        f'skip={skip} limit={limit} ({progress * 100}% compl.)')
    # 2. get update objects for text reuse index.
    solr_tr_passages = tr_passages_request.get('response').get('docs', [])
    solr_updates_needed = []
    for doc in solr_tr_passages:
        # get list of collection in ucoll_ss field
        ucoll_list = doc.get('ucoll_ss', [])
        if collection_id not in ucoll_list:
            continue
        ucoll_list.remove(collection_id)
        solr_updates_needed.append({
            'id': doc.get('id'),
            '_version_': doc.get('_version_'),
            'ucoll_ss': {
                'set': ucoll_list
            }
        })
    logger.info(f'(update) solr updates needed: {len(solr_updates_needed)}')
    # more than one
    if solr_updates_needed:
        result = update(
            url=settings.IMPRESSO_SOLR_PASSAGES_URL_UPDATE,
            todos=solr_updates_needed, logger=logger)
        result_response_header = result.get('responseHeader')
        result_adds = len(result.get('adds'))
        logger.info(
            f'(update) solr updates response={result_response_header}, '
            f'adds={result_adds}')
    # save all items there!
    return (page, loops, progress)
