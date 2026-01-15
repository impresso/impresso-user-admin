# Agent: Celery Tasks Development

This agent specializes in developing and maintaining Celery background tasks for the impresso-user-admin Django application.

## Expertise

- Creating new Celery tasks with proper decorators and configuration
- Writing helper functions for task operations
- Implementing job progress tracking
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

## Configuration Settings

Key Celery settings from `settings.py`:

- `CELERY_BROKER_URL` - Redis connection for Celery
- `IMPRESSO_GROUP_USER_PLAN_*` - User plan group names
- `DEFAULT_FROM_EMAIL` - Email sender address

## Key Models

- `Job` - Tracks long-running asynchronous tasks
- `UserBitmap` - User access permissions as bitmap
- `UserChangePlanRequest` - Plan upgrade/downgrade requests
- `UserSpecialMembershipRequest` - Special membership requests
- `Profile` - User profile with uid

## References

- Celery documentation: https://docs.celeryq.dev/
- Django documentation: https://docs.djangoproject.com/
