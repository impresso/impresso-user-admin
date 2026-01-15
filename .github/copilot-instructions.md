# GitHub Copilot Instructions for impresso-user-admin

## Repository Overview

This is a Django application that manages user-related information for the Impresso project's Master DB. The application uses **Celery** as the background task processing system for handling asynchronous operations like email sending, data exports, and collection management.

## Technology Stack

- **Framework**: Django (Python 3.12+)
- **Task Queue**: Celery with Redis as the broker
- **Database**: MySQL (managed via pymysql)
- **Search**: Apache Solr
- **Dependency Management**: pipenv
- **Type Checking**: mypy
- **Containerization**: Docker & docker-compose

## Project Structure

```
impresso-user-admin/
├── impresso/
│   ├── celery.py              # Celery application configuration
│   ├── settings.py            # Django settings
│   ├── models/                # Django models
│   ├── tasks/                 # Celery task definitions
│   ├── utils/
│   │   └── tasks/            # Task helper functions and utilities
│   ├── tests/                # Test suite
│   └── solr/                 # Solr integration utilities
├── .github/
│   ├── agents/               # Agent-specific instructions
│   └── copilot-instructions.md
└── manage.py
```

## Celery Task Organization

### Task Modules

The application organizes Celery tasks into two main directories:

1. **`impresso/tasks/`** - Contains Celery task decorators and task definitions
   - `userChangePlanRequest_task.py` - Plan change request tasks
   - `userSpecialMembershipRequest_tasks.py` - Special membership tasks

2. **`impresso/utils/tasks/`** - Contains helper functions used by tasks
   - `__init__.py` - Common utilities (pagination, job progress tracking)
   - `account.py` - User account and email operations
   - `collection.py` - Collection management in Solr
   - `export.py` - Data export to CSV/ZIP
   - `textreuse.py` - Text reuse passage operations
   - `userBitmap.py` - User permission bitmap updates
   - `email.py` - Email rendering and sending utilities
   - `userSpecialMembershipRequest.py` - Special membership operations

### Task Helper Functions

Common task utilities are provided in `impresso/utils/tasks/__init__.py`:

- `get_pagination()` - Calculate pagination for Solr queries with user limits
- `update_job_progress()` - Update job status and progress in DB and Redis
- `update_job_completed()` - Mark a job as completed
- `is_task_stopped()` - Check if user has stopped a job

Task states:
- `TASKSTATE_INIT` - Task initialization
- `TASKSTATE_PROGRESS` - Task in progress
- `TASKSTATE_SUCCESS` - Task completed successfully
- `TASKSTATE_STOPPED` - Task stopped by user

## Coding Conventions

### General Python

- Use Python 3.12+ type hints for all function signatures
- Follow PEP 8 style guidelines
- Use descriptive variable names
- Include docstrings for all public functions and classes
- Use f-strings for string formatting

### Django Specific

- Use Django ORM for all database operations
- Follow Django naming conventions for models, views, and managers
- Use Django's transaction management for atomic operations
- Settings should be accessed via `django.conf.settings`

### Celery Tasks

- Define tasks in `impresso/tasks/` directory
- Place helper functions in `impresso/utils/tasks/` directory
- Use `@shared_task` or `@app.task` decorators with appropriate configuration
- Always bind tasks when using `self` (e.g., for updating state)
- Include retry logic with exponential backoff for resilient tasks
- Use structured logging with task context (job_id, user_id)

Example task pattern:
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
def my_task(self, user_id: int) -> None:
    logger.info(f"[user:{user_id}] Starting task...")
    # Task implementation
```

### Logging

- Use structured logging with context: `logger.info(f"[job:{job.pk} user:{user.pk}] message")`
- Include relevant IDs in log messages (job, user, collection, etc.)
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, EXCEPTION
- Get logger via `get_task_logger(__name__)` in task files
- Use default_logger pattern: `default_logger = logging.getLogger(__name__)` in utility files

### Error Handling

- Catch specific exceptions rather than generic Exception
- Log exceptions with appropriate context
- Use exponential backoff for retries
- Handle database IntegrityErrors appropriately
- Validate user input before processing

### Email Operations

- Use `send_templated_email_with_context()` from `impresso/utils/tasks/email.py`
- Email templates are in `impresso/templates/emails/` (both .txt and .html)
- Always include both text and HTML versions
- Handle SMTP exceptions gracefully
- Log email sending status

### Solr Integration

- Use helper functions from `impresso/solr/` module
- Respect `settings.IMPRESSO_SOLR_EXEC_LIMIT` for query limits
- Respect `settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS` for maximum iterations
- Consider user's `max_loops_allowed` profile setting
- Use `find_all()` for queries and `update()` for updates
- Handle both main index and passages index (`IMPRESSO_SOLR_PASSAGES_URL_*`)

### Job Management

- Jobs track long-running asynchronous tasks
- Update job progress using `update_job_progress()`
- Check for user-initiated stops with `is_task_stopped()`
- Store task metadata in job.extra field as JSON
- Include pagination info in job updates

## Testing

### Running Tests

```bash
# Run all tests
ENV=dev pipenv run ./manage.py test

# Run specific test module
ENV=dev pipenv run ./manage.py test impresso.tests.utils.tasks.test_account

# Run with email backend visible
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend ENV=dev pipenv run ./manage.py test
```

### Test Organization

- Tests are in `impresso/tests/` directory
- Mirror the structure of the main codebase
- Use `TestCase` for standard tests
- Use `TransactionTestCase` for tests requiring DB transactions
- Clear `mail.outbox` between test cases
- Create default groups in setUp using `create_default_groups()`

### Test Conventions

- Name test methods descriptively: `test_send_email_plan_change`
- Use assertions that provide clear failure messages
- Test both success and error cases
- Mock external services (SMTP, Solr) when appropriate
- Test with different user plans and permissions

## Development Workflow

### Setting Up Environment

```bash
# Install dependencies
pipenv install

# Start Redis and MySQL
docker compose up -d

# Run migrations
ENV=dev pipenv run ./manage.py migrate

# Create superuser
ENV=dev pipenv run ./manage.py createsuperuser

# Run development server
ENV=dev pipenv run ./manage.py runserver

# Run Celery worker (in separate terminal)
ENV=dev pipenv run celery -A impresso worker -l info
```

### Type Checking

```bash
# Run mypy
pipenv run mypy --config-file ./.mypy.ini impresso
```

### Common Commands

```bash
# Create accounts
ENV=dev pipenv run ./manage.py createaccount user@example.com

# Sync collection
ENV=dev pipenv run ./manage.py synccollection <collection-id>

# Export query as CSV
ENV=dev pipenv run ./manage.py exportqueryascsv <user_id> "<solr_query>"

# Stop a job
ENV=dev pipenv run ./manage.py stopjob <job_id>
```

## Security Considerations

- Never commit secrets to source code
- Use environment variables for sensitive configuration
- Validate and sanitize user inputs
- Use Django's built-in security features
- Respect user permissions and bitmap access controls
- Use `mapper_doc_remove_private_collections()` to filter user content
- Apply `mapper_doc_redact_contents()` for content protection based on user bitmap

## Configuration

- Environment-specific settings via `.env` files (`.dev.env`, `.prod.env`)
- Use `ENV` environment variable to select configuration: `ENV=dev`
- See `.example.env` for available configuration options
- Settings loaded via `dotenv` in `impresso/base.py`

## Adding New Tasks

When adding new Celery tasks:

1. Create task definition in `impresso/tasks/` with proper decorators
2. Create helper functions in `impresso/utils/tasks/` if needed
3. Use structured logging with context
4. Implement retry logic with exponential backoff
5. Update job progress for long-running tasks
6. Check for user-initiated stops in loops
7. Handle errors gracefully
8. Add tests in `impresso/tests/tasks/`
9. Document the task purpose and parameters

## Resources

- Main repository: https://github.com/impresso/impresso-user-admin
- Impresso project: https://impresso-project.ch
- License: GNU Affero General Public License v3.0
