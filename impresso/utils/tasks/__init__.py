import math
from django.conf import settings


def get_pagination(skip, limit, total, job=None):
    limit = min(limit, settings.IMPRESSO_SOLR_EXEC_LIMIT)
    max_loops = min(
        job.creator.profile.max_loops_allowed,
        settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
    ) if job else settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
    page = 1 + skip / limit
    # get n of loops allowed
    loops = min(math.ceil(total / limit), max_loops)
    # 100% progress if there's no loops...
    progress = page / loops if loops > 0 else 1.0
    return page, loops, progress


def get_list_diff(a, b) -> list:
    return [
        item for item in a if item not in b
    ] + [
        item for item in b if item not in a
    ]
