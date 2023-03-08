import json
import requests
import logging
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from . import Bucket

default_logger = logging.getLogger(__name__)


def get_indexed_items(
    items_ids=[],
    lookup_field="id",
    skip=0,
    limit=None,
    solr_url=settings.IMPRESSO_SOLR_URL_SELECT,
    solr_auth=settings.IMPRESSO_SOLR_AUTH,
    logger=default_logger,
):
    rows = len(items_ids) if limit is None else limit
    res = requests.post(
        solr_url,
        auth=solr_auth,
        data={
            "q": " OR ".join(f"{lookup_field}:{value}" for value in items_ids),
            "fl": "id,ucoll_ss,_version_",
            "start": skip,
            "rows": rows,
            "wt": "json",
        },
    )
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.info("get_indexed_items FAILED data: {}".format(json.dumps(items_ids)))
        logger.info("error on url {}".format(settings.IMPRESSO_SOLR_URL_UPDATE))
        logger.info(res.text)
        logger.exception(err)
        raise

    total = res.json().get("response").get("numFound")
    logger.info(
        f"get_indexed_items items_ids={len(items_ids)} numFound={total} "
        f"skip={skip} limit={limit} rows={rows}"
    )
    return res.json().get("response").get("docs")


def set_indexed_items(
    todos,
    update_fl="id",
    solr_url=settings.IMPRESSO_SOLR_URL_UPDATE,
    solr_auth=settings.IMPRESSO_SOLR_AUTH_WRITE,
    logger=default_logger,
):
    res = requests.post(
        solr_url,
        auth=solr_auth,
        params={
            "commit": "true",
            "versions": "true",
            "fl": update_fl,
        },
        data=json.dumps(todos),
        json=True,
        headers={"content-type": "application/json; charset=UTF-8"},
    )
    # 5382743
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.info("sending data: {}".format(json.dumps(todos)))
        logger.info("error on url {}".format(settings.IMPRESSO_SOLR_URL_UPDATE))
        logger.info(res.text)
        logger.exception(err)
        raise
    return res.json()


class Collection(Bucket):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """

    PRIVATE = "PRI"
    SHARED = "PRI"
    PUBLIC = "PUB"
    DELETED = "DEL"

    STATUS_CHOICES = (
        (PRIVATE, "Private"),
        (SHARED, "Publicly available - only with a link"),
        (PUBLIC, "Public and indexed"),
        (DELETED, "In bin, ready to be deleted. No add items after this change."),
    )

    status = models.CharField(max_length=3, choices=STATUS_CHOICES)

    def add_items_to_index(
        self,
        items_ids=[],
        lookup_field="id",
        solr_url_select=settings.IMPRESSO_SOLR_URL_SELECT,
        solr_url_update=settings.IMPRESSO_SOLR_URL_UPDATE,
        solr_auth_select=settings.IMPRESSO_SOLR_AUTH,
        solr_auth_update=settings.IMPRESSO_SOLR_AUTH_WRITE,
        logger=default_logger,
    ):
        """
        return always docs
        """
        # get te desired items from SOLR along with their version
        # check if status is bin exit otherwise
        if self.status == Collection.DELETED:
            logger.info(
                f"Collection(pk:{self.pk}).add_items_to_index() STOPPED, status={self.status}"
            )
            return {
                "message": "collection is in BIN",
                "docs": [],
                "todos": [],
            }

        logger.info(
            f"Collection(pk:{self.pk}).add_items_to_index() - {len(items_ids)} items"
        )

        docs = get_indexed_items(
            items_ids=items_ids,
            lookup_field=lookup_field,
            solr_url=solr_url_select,
            solr_auth=solr_auth_select,
            logger=logger,
        )
        logger.info(
            f"Collection(pk:{self.pk}).add_items_to_index() - received {len(docs)} docs from solr."
        )

        todos = []
        for doc in docs:
            # get list of collection in ucoll_ss field
            ucoll_list = doc.get("ucoll_ss", [])
            # create the indexable name for current collection
            ucoll = self.pk
            if ucoll not in ucoll_list:
                ucoll_list.append(ucoll)
                todos.append(
                    {
                        "id": doc.get("id"),
                        "_version_": doc.get("_version_"),
                        "ucoll_ss": {"set": list(set(ucoll_list))},
                    }
                )
            else:
                logger.info(f'{ucoll} already in the ucoll list of {doc.get("id")}')

        if todos:
            logger.info(
                "Collection(pk:{}).add_items_to_index() for {} items ({} solr docs to update)...".format(
                    self.pk,
                    len(items_ids),
                    len(todos),
                )
            )
            set_indexed_items(
                todos=todos,
                solr_url=solr_url_update,
                solr_auth=solr_auth_update,
                logger=logger,
            )
            logger.info(
                "Collection(pk:{}) add_items_to_index() SUCCESS for {} items ({} docs updated)!".format(
                    self.pk,
                    len(items_ids),
                    len(todos),
                )
            )
        else:
            logger.info(
                "Collection(pk:{}).add_items_to_index() Nothing to do, all items are there already.".format(
                    self.pk
                )
            )

        # add collectionsto tr_items
        return {
            "message": "done",
            "docs": [{"id": id} for id in items_ids],
            "todos": todos,
        }

    def remove_items_from_index(self, items_ids=[], logger=None):
        """
        Remove selected items_ids from this collection
        """
        if not items_ids:
            if logger:
                logger.info(
                    "Collection {} remove_items_from_index, for {} items ..., nothing to do".format(
                        self.pk, len(items_ids)
                    )
                )
            return
        # get te desired items from SOLR along with their version
        if logger:
            logger.info(
                "Collection {} remove_items_from_index for {} items ...".format(
                    self.pk, len(items_ids)
                )
            )
        docs = get_indexed_items(items_ids)
        todos = []
        for doc in docs:
            # get list of collection in ucoll_ss field
            ucoll_list = set(doc.get("ucoll_ss", []))
            # create the indexable name for current collection
            ucoll = self.pk
            if ucoll not in ucoll_list:
                # print('Collection {} not in ucoll_list for id {}, skip.'.format(self.pk, doc.get('id')))
                continue
            ucoll_list.remove(ucoll)

            todos.append(
                {
                    "id": doc.get("id"),
                    "_version_": doc.get("_version_"),
                    "ucoll_ss": {"set": list(ucoll_list)},
                }
            )
        if not todos:
            if logger:
                logger.info(
                    "Collection {} remove_items_from_index nothing to do :)".format(
                        self.pk
                    )
                )
            return

        contents = set_indexed_items(todos=todos)
        if logger:
            logger.info(
                "Collection {} remove_items_from_index SUCCESS for {} items ({} docs updated)!".format(
                    self.pk,
                    len(items_ids),
                    len(todos),
                )
            )

        print(contents)

    def update_count_items(self, logger=default_logger):
        logger.info(f"Collection(pk:{self.pk}).update_count_items ...")
        res = requests.post(
            settings.IMPRESSO_SOLR_URL_SELECT,
            auth=settings.IMPRESSO_SOLR_AUTH,
            data={
                "q": "ucoll_ss:{}".format(self.pk),
                "fl": "id",
                "rows": 0,
                "wt": "json",
            },
        )
        res.raise_for_status()

        count_items = int(res.json().get("response").get("numFound"))
        logger.info(
            "Collection(pk:{}).update_count_items SUCCESS total:{}".format(
                self.pk,
                count_items,
            )
        )

        self.count_items = count_items
        self.save()
        return count_items

    class Meta(Bucket.Meta):
        db_table = "collections"
        verbose_name_plural = "collections"
