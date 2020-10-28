import logging
from django.conf import settings
from . import get_pagination, get_list_diff
from ...solr import find_all, update
# from ..models import Job

logger = logging.getLogger(__name__)


def update_collections_in_tr_passages(
    solr_content_items=[], skip=0, limit=100
):
    """
    :param int skip_trp: Skip n TR passages from the query (solr `start` param)
    :param int limit_trp: limit TR passages from the query (solr `rows` param)
    """
    # 1. get content items ids to be used in TR query
    items_ids = [doc['id'] for doc in solr_content_items]
    # 3. get collection per content item as a dict
    items_dict = {
        doc['id']: doc['ucoll_ss']
        for doc in solr_content_items}
    # 3. get current collection and _version_ from
    #    IMPRESSO_SOLR_PASSAGES_URL_SELECT endpoint
    tr_passages = find_all(
        q=' OR '.join(map(lambda id: f'ci_id_s:{id}', items_ids)),
        url=settings.IMPRESSO_SOLR_PASSAGES_URL_SELECT,
        fl='id,ucoll_ss,_version_,ci_id_s',
        skip=skip,
        limit=limit,
        logger=None)
    total_tr_passages = tr_passages['response']['numFound']
    logger.info(
        f'(update) q=<tr_passages for given ci ids> total={total_tr_passages} '
        f'skip={skip} limit={limit}')
    # No passages (or no more passages) present, exit.
    if total_tr_passages == 0:
        return
    # this list will contain solr items for the update endpoint
    solr_updates_needed = []
    # loop through all tr passages
    for tr_passage in tr_passages['response']['docs']:
        # get list of collection in TR ucoll_ss field
        tr_ucolls = tr_passage.get('ucoll_ss', [])
        # get list of collections in related content items
        ci_ucolls = items_dict[tr_passage['ci_id_s']]
        # get differences between the items collection and the current TR
        missing_ucolls = get_list_diff(tr_ucolls, ci_ucolls)
        if missing_ucolls:
            solr_updates_needed.append({
                'id': tr_passage.get('id'),
                '_version_': tr_passage.get('_version_'),
                'ucoll_ss': {
                    'set': ci_ucolls
                }
            })
    logger.info(
        f'(update) solr updates needed for TR: {len(solr_updates_needed)}')

    if solr_updates_needed:
        result = update(
            url=settings.IMPRESSO_SOLR_PASSAGES_URL_UPDATE,
            todos=solr_updates_needed, logger=logger)
        result_response_header = result.get('responseHeader')
        result_adds = len(result.get('adds'))
        logger.info(
            f'(update) solr updates response={result_response_header}, '
            f'adds={result_adds}')

    # check whether it is done
    if total_tr_passages > skip + limit:
        update_collections_in_tr_passages(
            solr_content_items=solr_content_items, skip=skip + limit,
            limit=limit)


def sync_collections_in_tr_passages(
    collection_id=None, skip=0, limit=100
) -> (int, int, float):
    """
    Add collections id in corresponding tr_passages (given their content items)
    :param collection_id: if no collection_id is given, all collections are
        loaded.
    :type collection_id: str or None
    :param int skip: Skip n content items from the query (solr `start` param)
    :param int limit: limit n content items from the query (solr `rows` param)
    :return: a pagination tuple
    :rtype: tuple
    """
    query = f'ucoll_ss:{collection_id}' if collection_id else 'ucoll_ss:*'
    # 1. get all content items having at least a collection
    content_items = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_URL_SELECT,
        fl='id,ucoll_ss',
        skip=skip,
        limit=limit,
        logger=logger)
    total_content_items = content_items['response']['numFound']
    page, loops, progress = get_pagination(
        skip=skip, limit=limit, total=total_content_items)
    logger.info(
        f'q={query} numFound={total_content_items} '
        f'skip={skip} limit={limit} ({progress * 100}% compl.)')
    # delegate updates to a specific function
    update_collections_in_tr_passages(
        solr_content_items=content_items['response']['docs'],
        limit=50)
    # save all items there!
    return (page, loops, progress)
