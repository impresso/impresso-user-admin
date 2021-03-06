import logging
from django.conf import settings
from django.db.utils import IntegrityError
from . import get_pagination, get_list_diff
from ...solr import find_all, update
from ...models import Collection, CollectableItem

default_logger = logging.getLogger(__name__)

METHOD_ADD_TO_INDEX = 'METHOD_ADD_TO_INDEX'
METHOD_DEL_FROM_INDEX = 'METHOD_DEL_FROM_INDEX'


def update_collections_in_tr_passages(
    solr_content_items=[], skip=0, limit=100,
    logger=default_logger
):
    """
    :param int skip_trp: Skip n TR passages from the query (solr `start` param)
    :param int limit_trp: limit TR passages from the query (solr `rows` param)
    """
    # 1. get content items ids to be used in TR query
    items_ids = [doc['id'] for doc in solr_content_items]
    # 3. get collection per content item as a dict
    items_dict = {
        doc['id']: doc.get('ucoll_ss', [])
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
    collection_id=None, skip=0, limit=100,
    logger=default_logger
) -> (int, int, float):
    '''
    Add collections id in corresponding tr_passages (given their content items)
    :param collection_id: if no collection_id is given, all collections are
        loaded.
    :type collection_id: str or None
    :param int skip: Skip n content items from the query (solr `start` param)
    :param int limit: limit n content items from the query (solr `rows` param)
    :return: a pagination tuple
    :rtype: tuple
    '''
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


def delete_collection(
    collection_id, limit=100, logger=default_logger
) -> (int, int, float):
    '''
    '''
    try:
        collection = Collection.objects.get(pk=collection_id)
        query = f'ucoll_ss:{collection.pk}'
    except Collection.DoesNotExist:
        logger.info('Collection does not exist in DB, remove from SOLR.')
        query = f'ucoll_ss:{collection_id}'
    # 1. get all collection related content items
    content_items = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_URL_SELECT,
        fl='id,ucoll_ss,_version_',
        skip=0,
        limit=limit,
        logger=logger)
    total_content_items = content_items['response']['numFound']
    page, loops, progress = get_pagination(
        skip=0, limit=limit, total=total_content_items)
    logger.info(
        f'q={query} numFound={total_content_items} '
        f'skip=0 limit={limit} ({progress * 100}% compl.)')
    solr_updates_needed = []
    solr_content_items = content_items.get('response').get('docs', [])
    for doc in solr_content_items:
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
            url=settings.IMPRESSO_SOLR_URL_UPDATE,
            todos=solr_updates_needed, logger=logger)
        result_response_header = result.get('responseHeader')
        result_adds = len(result.get('adds'))
        logger.info(
            f'(update) solr updates response={result_response_header}, '
            f'adds={result_adds}')
    # remove collectable items from db
    items_ids = [doc['id'] for doc in solr_content_items]
    logger.info(f'(db) db CollectableItem to delete={len(items_ids)}')
    db_removal = CollectableItem.objects.filter(
        collection_id=collection_id
    ).filter(
        item_id__in=items_ids
    ).delete()
    logger.info(f'(db) db CollectableItem deleted={db_removal}')
    # remove collections from text passages
    updated_content_items = find_all(
        q=' OR '.join(map(lambda id: f'id:{id}', items_ids)),
        url=settings.IMPRESSO_SOLR_URL_SELECT,
        fl='id,ucoll_ss,_version_',
        skip=0,
        limit=limit,
        logger=logger)
    update_collections_in_tr_passages(
        solr_content_items=updated_content_items.get('response').get('docs'),
        limit=50)
    return (page, loops, progress)


def sync_query_to_collection(
    collection_id, query, content_type, skip=0, limit=100,
    method=METHOD_ADD_TO_INDEX,
    logger=default_logger
) -> (int, int, float, int, int):
    collection = Collection.objects.get(pk=collection_id)
    content_items = find_all(
        q=query,
        url=settings.IMPRESSO_SOLR_URL_SELECT,
        fl='id,ucoll_ss,_version_,score',
        skip=skip,
        limit=limit,
        sort='score DESC,id ASC',
        logger=logger)
    total_content_items = content_items['response']['numFound']
    logger.info(content_items['responseHeader'])
    page, loops, progress = get_pagination(
        skip=skip, limit=limit, total=total_content_items)

    solr_content_items = content_items.get('response').get('docs', [])
    collection.count_items = int(skip * limit + int(len(solr_content_items)))
    collection.save()
    logger.info(
        f'coll={collection.pk} q={query} numFound={total_content_items} '
        f'count_items={collection.count_items} '
        f'skip={skip} limit={limit} ({progress * 100}% compl.)')
    if method == METHOD_ADD_TO_INDEX:
        try:
            CollectableItem.objects.bulk_create(map(
                lambda doc: CollectableItem(
                    item_id=doc.get('id'),
                    content_type=content_type,
                    collection_id=collection_id,
                    search_query_score=doc.get('score')
                ),
                solr_content_items
            ), ignore_conflicts=True)
        except IntegrityError as e:
            logger.exception(e)
    # add collection id to solr items.
    # collection.add_items_to_index(items_ids=items_ids, logger=logger)
    solr_updates_needed = []
    for doc in solr_content_items:
        # get list of collection in ucoll_ss field
        ucoll_list = doc.get('ucoll_ss', [])
        if method == METHOD_ADD_TO_INDEX:
            if collection_id in ucoll_list:
                continue
            ucoll_list.append(collection_id)
        elif method == METHOD_DEL_FROM_INDEX:
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
            url=settings.IMPRESSO_SOLR_URL_UPDATE,
            todos=solr_updates_needed, logger=logger)
        result_response_header = result.get('responseHeader')
        result_adds = len(result.get('adds'))
        logger.info(
            f'(update) solr updates response={result_response_header}, '
            f'adds={result_adds}')
    # get updated collections.
    items_ids = [doc['id'] for doc in solr_content_items]
    updated_content_items = find_all(
        q=' OR '.join(map(lambda id: f'id:{id}', items_ids)),
        url=settings.IMPRESSO_SOLR_URL_SELECT,
        fl='id,ucoll_ss,_version_',
        skip=0,
        limit=len(items_ids),
        logger=logger)
    update_collections_in_tr_passages(
        solr_content_items=updated_content_items.get('response').get('docs'),
        limit=50)

    return (page, loops, progress, total_content_items, min(
        total_content_items,
        loops * limit
    ))
