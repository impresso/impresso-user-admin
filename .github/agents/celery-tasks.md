# Agent: Celery Tasks Development

This agent specializes in developing and maintaining Celery background tasks for the impresso-user-admin Django application.

## Expertise

- Creating new Celery tasks with proper decorators and configuration
- Writing helper functions for task operations
- Implementing job progress tracking
- Integrating with Solr for search and indexing
- Managing user permissions and access control
- Error handling and retry logic
- Structured logging

## Task Development Guidelines

### Task Definition Structure

All Celery tasks should follow this pattern:

```python
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def task_name(self, param: type) -> return_type:
    """
    Task description.
    
    Args:
        param: Description
        
    Returns:
        Description
    """
    logger.info(f"[context] Starting task with param={param}")
    # Implementation
```

### File Organization

- **Task definitions**: Place in `impresso/tasks/`
  - Use descriptive filenames ending in `_task.py` or `_tasks.py`
  - Import and use helper functions from utils
  
- **Helper functions**: Place in `impresso/utils/tasks/`
  - Reusable logic that can be called by multiple tasks
  - Database operations, API calls, data processing
  - Keep helpers stateless and testable

### Job Progress Tracking

For long-running tasks, use the Job model to track progress:

```python
from impresso.models import Job
from impresso.utils.tasks import (
    update_job_progress,
    update_job_completed,
    is_task_stopped,
    TASKSTATE_PROGRESS,
)

def long_running_task(self, job_id: int):
    job = Job.objects.get(pk=job_id)
    
    # Check if user stopped the job
    if is_task_stopped(task=self, job=job, progress=0.0, logger=logger):
        return
    
    # Update progress
    update_job_progress(
        task=self,
        job=job,
        progress=0.5,  # 50%
        taskstate=TASKSTATE_PROGRESS,
        extra={"current_step": "processing"},
        message="Processing data...",
        logger=logger,
    )
    
    # Complete the job
    update_job_completed(
        task=self,
        job=job,
        extra={"results": "summary"},
        message="Task completed successfully",
        logger=logger,
    )
```

### Pagination with User Limits

When processing large result sets from Solr:

```python
from impresso.utils.tasks import get_pagination
from django.conf import settings

# Calculate pagination respecting user and system limits
page, loops, progress, max_loops = get_pagination(
    skip=skip,
    limit=limit,
    total=total,
    job=job,
    ignore_max_loops=False  # Set True only for admin operations
)

logger.info(
    f"[job:{job.pk} user:{job.creator.pk}] "
    f"page={page} loops={loops} progress={progress * 100:.2f}%"
)

# Loop through pages
if page < loops:
    # More pages to process
    skip += limit
    # Continue processing
else:
    # All pages processed
    pass
```

### Solr Integration

Use the provided Solr utilities:

```python
from impresso.solr import find_all, update
from django.conf import settings

# Query Solr
results = find_all(
    q="content_txt_fr:*",
    fl="id,title,date",
    skip=0,
    limit=100,
    logger=logger
)

total = results["response"]["numFound"]
docs = results["response"]["docs"]

# Update Solr (requires write credentials)
update_result = update(
    url=settings.IMPRESSO_SOLR_URL_UPDATE,
    todos=[
        {
            "id": "doc-123",
            "ucoll_ss": {"add": ["collection-id"]},
            "_version_": doc_version
        }
    ],
    logger=logger
)
```

### Access Control and Content Redaction

Always respect user permissions:

```python
from impresso.utils.bitmask import BitMask64
from impresso.utils.solr import (
    mapper_doc_remove_private_collections,
    mapper_doc_redact_contents,
)

# Get user's bitmap for access control
user_bitmask = BitMask64(job.creator.profile.user_bitmap_key)

# Check if user has special no-redaction privilege
user_allow_no_redaction = job.creator.groups.filter(
    name=settings.IMPRESSO_GROUP_USER_PLAN_NO_REDACTION
).exists()

# Process each document
for doc in docs:
    # Remove private collections from user's view
    doc = mapper_doc_remove_private_collections(
        doc=doc,
        prefix=job.creator.profile.uid
    )
    
    # Redact content based on permissions (unless user has privilege)
    if not user_allow_no_redaction:
        doc = mapper_doc_redact_contents(
            doc=doc,
            user_bitmask=user_bitmask,
        )
```

### Email Operations

Use the email utility functions:

```python
from impresso.utils.tasks.email import send_templated_email_with_context
from django.conf import settings

success = send_templated_email_with_context(
    template='notification_name',  # Uses emails/notification_name.txt and .html
    subject='Email Subject',
    from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
    to=[user.email],
    cc=[settings.DEFAULT_FROM_EMAIL],
    reply_to=[settings.DEFAULT_FROM_EMAIL],
    context={
        'user': user,
        'custom_data': 'value',
    },
    logger=logger,
    fail_silently=False,
)
```

### Error Handling

Implement proper error handling with retries:

```python
from django.db.utils import IntegrityError
from requests.exceptions import RequestException

@shared_task(
    bind=True,
    autoretry_for=(RequestException, IntegrityError),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def resilient_task(self, param: str):
    try:
        # Task logic
        pass
    except ValueError as e:
        # Don't retry validation errors
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        # Log and let Celery handle retry
        logger.exception(f"Unexpected error: {e}")
        raise
```

### Logging Best Practices

Use structured logging with context:

```python
# Always include relevant IDs
logger.info(f"[job:{job.pk} user:{user.pk}] Starting operation")

# Include metrics
logger.info(
    f"[job:{job.pk}] Processed {count} items in {qtime}ms "
    f"(page {page}/{loops}, {progress*100:.2f}%)"
)

# Use appropriate levels
logger.debug(f"Debug info: {data}")
logger.info(f"Operation completed successfully")
logger.warning(f"Potential issue: {warning}")
logger.error(f"Error occurred: {error}")
logger.exception(f"Exception with traceback: {e}")  # Includes stack trace
```

## Testing Tasks

Create tests in `impresso/tests/tasks/`:

```python
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from impresso.tasks.my_task import my_task
from django.core import mail

class TestMyTask(TransactionTestCase):
    """
    Test my_task functionality.
    
    Run with:
    ENV=dev pipenv run ./manage.py test impresso.tests.tasks.TestMyTask
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        # Create default groups
        from impresso.signals import create_default_groups
        create_default_groups(sender="impresso")
    
    def test_task_execution(self):
        # Clear mail outbox
        mail.outbox = []
        
        # Run task
        result = my_task(user_id=self.user.id)
        
        # Assertions
        self.assertEqual(result, expected_value)
        self.assertEqual(len(mail.outbox), 1)
```

## Common Patterns

### Processing Collections

```python
def process_collection_items(
    collection_id: str,
    job: Job,
    skip: int = 0,
    limit: int = 100,
    logger=default_logger
) -> Tuple[int, int, float]:
    """Process items in a collection with pagination."""
    
    # Get collection
    collection = Collection.objects.get(pk=collection_id)
    
    # Query Solr for collection items
    query = f"ucoll_ss:{collection_id}"
    results = find_all(
        q=query,
        fl="id,title,date",
        skip=skip,
        limit=limit,
        logger=logger
    )
    
    total = results["response"]["numFound"]
    page, loops, progress, max_loops = get_pagination(
        skip=skip, limit=limit, total=total, job=job
    )
    
    # Process items
    for doc in results["response"]["docs"]:
        # Process each item
        pass
    
    return page, loops, progress
```

### Export to CSV/ZIP

```python
import csv
from zipfile import ZipFile, ZIP_DEFLATED

def export_results_to_csv(job: Job, results: list, fieldnames: list):
    """Export results to CSV and create ZIP archive."""
    
    csv_path = job.attachment.upload.path
    
    with open(csv_path, mode='a', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            delimiter=';',
            quoting=csv.QUOTE_MINIMAL,
            fieldnames=fieldnames,
        )
        
        # Write header on first page
        if skip == 0:
            writer.writeheader()
        
        # Write rows
        for row in results:
            filtered_row = {k: v for k, v in row.items() if k in fieldnames}
            writer.writerow(filtered_row)
    
    # Create ZIP when done
    zip_path = f"{csv_path}.zip"
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
        zipf.write(csv_path, basename(csv_path))
    
    # Update job attachment
    job.attachment.upload.name = f"{job.attachment.upload.name}.zip"
    job.attachment.save()
    
    # Remove original CSV
    if os.path.exists(csv_path):
        os.remove(csv_path)
```

## Configuration Settings

Key Celery and Solr settings from `settings.py`:

- `CELERY_BROKER_URL` - Redis connection for Celery
- `IMPRESSO_SOLR_URL` - Main Solr index URL
- `IMPRESSO_SOLR_PASSAGES_URL_SELECT` - Text reuse passages query URL
- `IMPRESSO_SOLR_PASSAGES_URL_UPDATE` - Text reuse passages update URL
- `IMPRESSO_SOLR_EXEC_LIMIT` - Maximum rows per Solr query (default: 100)
- `IMPRESSO_SOLR_EXEC_MAX_LOOPS` - Maximum query loops (default: 100)
- `IMPRESSO_GROUP_USER_PLAN_*` - User plan group names
- `DEFAULT_FROM_EMAIL` - Email sender address

## Key Models

- `Job` - Tracks long-running asynchronous tasks
- `Collection` - User-created collections of content items
- `CollectableItem` - Individual items in collections
- `UserBitmap` - User access permissions as bitmap
- `UserChangePlanRequest` - Plan upgrade/downgrade requests
- `Profile` - User profile with uid and max_loops_allowed

## References

- Celery documentation: https://docs.celeryq.dev/
- Django documentation: https://docs.djangoproject.com/
- Apache Solr documentation: https://solr.apache.org/guide/
