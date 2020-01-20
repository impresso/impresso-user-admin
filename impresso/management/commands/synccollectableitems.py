import logging, timeit, requests, itertools, datetime, json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from impresso.models import CollectableItem
from impresso.solr import find_collections_by_ids

# choose the right logger
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'store all collections for each collected items'

    def add_arguments(self, parser):
        parser.add_argument('--skip', nargs='?', type=int, default=0)
        parser.add_argument('--newspaper', nargs='?', type=str, default=None)
        parser.add_argument('--collection_id', nargs='?', type=str, default=None)
        parser.add_argument('--user_id', nargs='?', type=int, default=0)

    def handle(self, skip, newspaper, collection_id, user_id, *args, **options):
        self.stdout.write('sync all items! SKIP=%s'% skip)
        self.stdout.write('solr target: %s' % settings.IMPRESSO_SOLR_URL_SELECT)
        self.stdout.write('mysql port: %s' % settings.DATABASES['default']['PORT'])
        self.stdout.write('mysql name: %s' % settings.DATABASES['default']['NAME'])
        self.stdout.write('-- opt arg SKIP=%s'% skip)
        self.stdout.write('-- opt arg newspaper=%s' % newspaper)
        self.stdout.write('-- opt arg collection_id=%s' % collection_id)
        self.stdout.write('-- opt arg user_id=%s' % user_id)
        items_queryset = CollectableItem.objects.filter()
        if newspaper:
            items_queryset = items_queryset.filter(item_id__startswith=newspaper)
        if collection_id:
            items_queryset = items_queryset.filter(collection_id=collection_id)
        if user_id:
            items_queryset = items_queryset.filter(collection__creator_id=user_id)
        self.stdout.write('-- query %s' % items_queryset.query)
        items = items_queryset.values_list('item_id', flat=True).order_by('item_id').distinct()
        total = items.count()
        self.stdout.write('total items %s' % total)
        logger.debug('starting sync %s items' % total)
        logger.debug('main SQL query: "%s"' % items.query)
        c = 0
        runtime = 0.0
        chunksize = 50
        init = timeit.default_timer()

        paginator = Paginator(items, chunksize)
        self.stdout.write('total loops %s' % paginator.num_pages)
        logger.debug('loops needed: %s (%s per loop)' % (paginator.num_pages, chunksize))
        # for page in pages
        for page in range(skip + 1, paginator.num_pages + 1):
            if c == 0:
                start = timeit.default_timer()
                # add initial skipped elements
                c = skip * chunksize

            self.stdout.write('\nloop n. %s of %s\n---' % (page, paginator.num_pages))
            # get object list
            uids = [uid for uid in paginator.page(page).object_list]

            # get ALL the collections for those objects
            colls = CollectableItem.objects.filter(item_id__in=uids).values(
                'item_id',
                'collection__pk',
                'collection__status'
            )

            docs = { x['id'] : x for x in find_collections_by_ids(ids=uids) }
            ucolls = [];

            for uid, group in itertools.groupby(colls, key=lambda x:x.get('item_id')):
                ucoll = list(filter(lambda x: x.get('collection__status') != 'DEL', list(group)))
                # filter by collection status
                ucoll_ss = [x.get('collection__pk') for x in ucoll]
                # calculate diff between mysql and solr docs
                doc = docs.get(uid, None)

                if doc is None:
                    logger.error('AttributeError: unknown uid "%s" in SOLR %s' % (uid, settings.IMPRESSO_SOLR_URL_SELECT))
                    continue

                diffs = set(ucoll_ss).symmetric_difference(set(doc.get('ucoll_ss', [])))

                if len(diffs) > 0:
                    ucolls.append({
                        'id': uid,
                        'ucoll_ss': {
                            'set': ucoll_ss
                        },
                        '_version_': doc.get('_version_'),
                    })

            if len(ucolls):
                self.stdout.write('n. atomic updates todo: %s / %s' % (len(ucolls), len(uids)))

                # print(ucolls)
                res = requests.post(settings.IMPRESSO_SOLR_URL_UPDATE,
                    auth = settings.IMPRESSO_SOLR_AUTH_WRITE,
                    params = {
                        'commit': 'true',
                        'versions': 'true',
                    },
                    data = json.dumps(ucolls),
                    json=True,
                    headers = {
                        'content-type': 'application/json; charset=UTF-8'
                    },
                )

                if res.status_code == 409:
                    print(res.json())

                res.raise_for_status()
            else:
                self.stdout.write('no atomic updates needed, collections are synced!')

            # updata completion count
            c = c + len(uids)
            stop = timeit.default_timer()
            runtime = stop - start
            completion =  float(c) / total

            self.stdout.write('runtime: %s s' % runtime)
            self.stdout.write('completion: %s %%' % (completion * 100))
            self.stdout.write('ETA: %s s.' % datetime.timedelta(seconds=(runtime * 100 / completion)))
            # group by uid
        logger.debug('syncing completed on %s items in %s s' % (total, runtime))
