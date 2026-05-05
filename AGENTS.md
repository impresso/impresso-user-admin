## Repository Overview

This is a Django application that manages user-related information for the Impresso project's Master DB. The application uses **Celery** as the background task processing system for handling asynchronous operations like email sending and user account management.

## Technology Stack

- **Framework**: Django (Python 3.12+)
- **Task Queue**: Celery with Redis as the broker
- **Database**: MySQL (managed via pymysql)
- **Dependency Management**: pipenv
- **Type Checking**: mypy
- **Containerization**: Docker & docker-compose

## Project Structure, AI & Agent Instructions

This repository contains AI coding instructions and architectural guidelines in:

- `.github/copilot-instructions.md`

Those instructions define:

- Coding style
- Task conventions
- Architectural constraints

All agents and contributors MUST follow those rules when adding or modifying tasks.

## Testing and Celery Behavior

### Custom test runner

The project uses a custom Django test runner configured in [impresso/settings.py](impresso/settings.py#L104):

- `TEST_RUNNER = "impresso.tests.test_runner.TestRunner"`

The runner implementation is in [impresso/tests/test_runner.py](impresso/tests/test_runner.py#L1) and enables these Celery settings for tests:

- `CELERY_TASK_ALWAYS_EAGER=True`
- `CELERY_TASK_EAGER_PROPAGATES=True`
- `CELERY_TASK_STORE_EAGER_RESULT=False`

### Practical implications for tests

- Calls to Celery queue APIs like `.delay()` and `.apply_async()` run inline during tests in this repository.
- Exceptions raised by task code propagate to the test process (because eager propagates is enabled).
- For scheduling logic, do not wait for wall-clock execution in tests. Instead, patch the enqueue call and assert arguments.

### `apply_async(..., eta=...)` in tests

When eager mode is enabled by the custom test runner, `apply_async(..., eta=...)` does not behave like a real delayed worker schedule. The call executes immediately in-process, while `eta` is still passed as metadata.

For scheduling assertions, patch the task method and assert it was called with the expected `eta` and kwargs, for example:

```python
with patch(
    "impresso.tasks.userSpecialMembershipRequest_tasks.revoke_special_membership_request.apply_async"
) as mock_apply_async:
    _schedule_temporary_revocation(req)

    mock_apply_async.assert_called_once()
    _, call_kwargs = mock_apply_async.call_args
    assert call_kwargs["kwargs"] == {"instance_id": req.pk}
    assert "eta" in call_kwargs
```

## Email and templates

### Overview

Email functionality is split into two layers:

1. **Utility functions** in `impresso/utils/tasks/account.py` – generic, reusable helpers for sending emails related to user accounts (registration, activation, password reset, magic links, plan changes, etc.).
2. **Low-level sending utility** in `impresso/utils/tasks/email.py` – provides `send_templated_email_with_context()`, which renders templates and sends via Django's `EmailMultiAlternatives`.

### Where templates live

All email templates are stored in `impresso/templates/emails/`. Every email requires two files:

- `<name>.txt` – plain-text version
- `<name>.html` – HTML version

### Adding a new account-related email task

1. Add a helper function to `impresso/utils/tasks/account.py` following the existing patterns (e.g. `send_magic_link_email`, `send_email_password_reset`).
2. Use `send_templated_email_with_context()` from `impresso/utils/tasks/email.py` for sending.
3. Create both `<name>.txt` and `<name>.html` templates in `impresso/templates/emails/`.
4. Add tests in `impresso/tests/utils/tasks/test_account.py`.

### `send_templated_email_with_context` signature (from `impresso/utils/tasks/email.py`)

```python
send_templated_email_with_context(
    template: str,          # template name prefix (no extension)
    subject: str,
    from_email: str,
    to: list[str],
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
    context: dict | None = None,
    attachments: list | None = None,
    template_dir: str = "emails",
    logger: Logger = ...,
    fail_silently: bool = False,
) -> bool
```

### Example: magic-link email

The `send_magic_link_email` function in `impresso/utils/tasks/account.py` demonstrates the recommended pattern for generic account emails:

```python
send_magic_link_email(
    user_id=123,
    token="<token>",
    magic_link_callback_url="https://dev.impresso-project.ch/institutions-access/magic-link",
)
```

The function appends `?token=<token>` to `magic_link_callback_url` and passes the full URL as `magic_link` to the template context.
