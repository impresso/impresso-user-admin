# Agent: Testing

This agent specializes in writing and maintaining tests for the impresso-user-admin Django application.

## Expertise

- Writing Django unit tests and integration tests
- Testing Celery tasks and async operations
- Mocking external services (Solr, SMTP)
- Testing email functionality
- Database transaction testing
- User permission and access control testing

## Test Framework

The project uses Django's built-in testing framework based on unittest.

### Test Types

1. **TestCase** - Standard test case with database rollback
   - Use for most tests
   - Database changes are rolled back after each test
   - Faster than TransactionTestCase

2. **TransactionTestCase** - Test case with transaction support
   - Use when testing transaction behavior
   - Use when testing signals that depend on commits
   - Database is flushed between tests (slower)

## Test Organization

### Directory Structure

```
impresso/tests/
├── __init__.py
├── test_runner.py          # Custom test runner
├── test_solr.py            # Solr integration tests
├── models/                 # Model tests
├── tasks/                  # Task tests
│   ├── __init__.py
│   └── test_*.py
└── utils/
    └── tasks/              # Task utility tests
        ├── __init__.py
        ├── test_account.py
        ├── test_userBitmap.py
        └── email.py
```

### Test File Naming

- Prefix test files with `test_`: `test_account.py`
- Mirror the structure of the code being tested
- Group related tests in the same file

### Test Class Naming

```python
class TestFeatureName(TestCase):
    """
    Test feature description.
    
    Run with:
    ENV=dev pipenv run ./manage.py test impresso.tests.path.TestFeatureName
    """
```

## Running Tests

```bash
# Run all tests
ENV=dev pipenv run ./manage.py test

# Run specific app tests
ENV=dev pipenv run ./manage.py test impresso

# Run specific test file
ENV=dev pipenv run ./manage.py test impresso.tests.utils.tasks.test_account

# Run specific test class
ENV=dev pipenv run ./manage.py test impresso.tests.utils.tasks.test_account.TestAccountPlanChange

# Run specific test method
ENV=dev pipenv run ./manage.py test impresso.tests.utils.tasks.test_account.TestAccountPlanChange.test_send_email_plan_change

# With console email backend (to see email output)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend ENV=dev pipenv run ./manage.py test

# With verbose output
ENV=dev pipenv run ./manage.py test --verbosity=2
```

## Test Structure

### Basic Test Template

```python
import logging
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.core import mail
from impresso.models import ModelName
from impresso.utils.tasks.module import function_to_test

logger = logging.getLogger("console")


class TestFeature(TestCase):
    """
    Test feature functionality.
    
    ENV=dev pipenv run ./manage.py test impresso.tests.module.TestFeature
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            first_name="Jane",
            last_name="Doe",
            password="testpass123",
            email="test@example.com",
        )
        
        # Create default groups (required for many tests)
        from impresso.signals import create_default_groups
        create_default_groups(sender="impresso")
        
        # Clear mail outbox
        mail.outbox = []
    
    def tearDown(self):
        """Clean up after each test method."""
        pass
    
    def test_feature_success(self):
        """Test successful feature execution."""
        # Arrange
        expected_result = "expected"
        
        # Act
        result = function_to_test(self.user.id)
        
        # Assert
        self.assertEqual(result, expected_result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Expected Subject")
```

### Testing with Transactions

```python
class TestFeatureWithTransaction(TransactionTestCase):
    """
    Test feature requiring transaction support.
    
    ENV=dev pipenv run ./manage.py test impresso.tests.module.TestFeatureWithTransaction
    """
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        from impresso.signals import create_default_groups
        create_default_groups(sender="impresso")
    
    def test_with_commit(self):
        """Test behavior after transaction commit."""
        # Your test code
        pass
```

## Testing Email Functionality

### Email Testing Pattern

```python
from django.core import mail
from django.conf import settings

def test_send_email(self):
    """Test email sending functionality."""
    # Clear outbox before test
    mail.outbox = []
    
    # Call function that sends email
    send_email_function(user_id=self.user.id)
    
    # Check email was sent
    self.assertEqual(len(mail.outbox), 1)
    
    # Check email properties
    email = mail.outbox[0]
    self.assertEqual(email.subject, "Expected Subject")
    self.assertEqual(email.to, [self.user.email])
    self.assertEqual(email.from_email, f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>")
    
    # Check email content
    self.assertIn("Dear Jane,", email.body)
    self.assertIn("expected text", email.body)
    
    # Check HTML alternative exists
    self.assertEqual(len(email.alternatives), 1)
    html_content, content_type = email.alternatives[0]
    self.assertEqual(content_type, "text/html")
    self.assertIn("<p>", html_content)

def test_multiple_emails(self):
    """Test when multiple emails are sent."""
    mail.outbox = []
    
    # Function sends email to user and staff
    send_emails_after_user_registration(self.user.id)
    
    # Check both emails sent
    self.assertEqual(len(mail.outbox), 2, "Should send email to user and staff")
    
    # Check first email (to user)
    self.assertEqual(mail.outbox[0].to, [self.user.email])
    
    # Check second email (to staff)
    self.assertEqual(mail.outbox[1].to, [settings.DEFAULT_FROM_EMAIL])
```

## Testing User Groups and Permissions

### Group Setup

```python
def setUp(self):
    """Set up user with specific plan."""
    self.user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    
    # Create default groups
    from impresso.signals import create_default_groups
    create_default_groups(sender="impresso")
    
    # Add user to specific plan
    group = Group.objects.get(name=settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER)
    self.user.groups.add(group)
    self.user.is_active = True
    self.user.save()

def test_user_permissions(self):
    """Test user has correct permissions."""
    # Check user is in group
    group_names = list(self.user.groups.values_list("name", flat=True))
    self.assertIn(settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER, group_names)
    
    # Check user bitmap
    from impresso.models import UserBitmap
    user_bitmap = UserBitmap.objects.get(user=self.user)
    self.assertEqual(
        user_bitmap.get_bitmap_as_int(),
        UserBitmap.USER_PLAN_RESEARCHER
    )
```

## Testing Celery Tasks

### Testing Task Execution

```python
from impresso.tasks.my_tasks import my_task
from impresso.models import Job

class TestCeleryTask(TransactionTestCase):
    """Test Celery task functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )
        from impresso.signals import create_default_groups
        create_default_groups(sender="impresso")
    
    def test_task_execution(self):
        """Test task executes successfully."""
        # Create job for tracking
        job = Job.objects.create(
            creator=self.user,
            type=Job.EXP,
            status=Job.RUN,
        )
        
        # Execute task (runs synchronously in tests)
        result = my_task.apply(args=[job.id])
        
        # Check result
        self.assertTrue(result.successful())
        
        # Refresh job from database
        job.refresh_from_db()
        self.assertEqual(job.status, Job.DONE)
```

### Testing Task Helpers

```python
from impresso.utils.tasks import get_pagination
from impresso.models import Job, Profile

def test_pagination(self):
    """Test pagination calculation."""
    # Create user with profile
    profile = Profile.objects.create(
        user=self.user,
        uid="test-user",
        max_loops_allowed=50
    )
    
    # Create job
    job = Job.objects.create(
        creator=self.user,
        type=Job.EXP,
    )
    
    # Test pagination
    page, loops, progress, max_loops = get_pagination(
        skip=0,
        limit=100,
        total=1000,
        job=job
    )
    
    self.assertEqual(page, 1)
    self.assertEqual(loops, 10)
    self.assertEqual(progress, 0.1)
```

## Testing Exceptions

### Exception Testing Pattern

```python
def test_exception_raised(self):
    """Test function raises appropriate exception."""
    with self.assertRaises(ValueError, msg="Should raise ValueError"):
        function_that_should_fail(invalid_param="bad")

def test_user_not_found(self):
    """Test handling of non-existent user."""
    with self.assertRaises(User.DoesNotExist):
        function_requiring_user(user_id=99999)

def test_validation_error(self):
    """Test validation error handling."""
    from django.core.exceptions import ValidationError
    
    with self.assertRaises(ValidationError):
        function_with_validation(invalid_data)
```

## Mocking External Services

### Mocking Solr

```python
from unittest.mock import patch, MagicMock

@patch('impresso.solr.find_all')
def test_with_mocked_solr(self, mock_find_all):
    """Test function with mocked Solr response."""
    # Setup mock response
    mock_find_all.return_value = {
        "response": {
            "numFound": 10,
            "docs": [
                {"id": "doc-1", "title": "Test Document"},
                {"id": "doc-2", "title": "Another Document"},
            ]
        },
        "responseHeader": {"QTime": 5}
    }
    
    # Call function that uses Solr
    result = function_using_solr(query="test")
    
    # Verify mock was called correctly
    mock_find_all.assert_called_once_with(
        q="test",
        fl="id,title",
        skip=0,
        logger=mock.ANY
    )
    
    # Check result
    self.assertEqual(len(result), 2)
```

### Mocking SMTP

```python
from unittest.mock import patch
import smtplib

@patch('smtplib.SMTP')
def test_email_smtp_error(self, mock_smtp):
    """Test handling of SMTP errors."""
    # Setup mock to raise exception
    mock_smtp.side_effect = smtplib.SMTPException("Connection failed")
    
    # Call function that sends email
    with self.assertRaises(smtplib.SMTPException):
        send_email_function(user_id=self.user.id)
```

## Testing Database Models

```python
from impresso.models import Collection, CollectableItem

def test_model_creation(self):
    """Test model instance creation."""
    collection = Collection.objects.create(
        name="Test Collection",
        creator=self.user,
        description="Test description"
    )
    
    self.assertEqual(collection.name, "Test Collection")
    self.assertEqual(collection.creator, self.user)
    self.assertIsNotNone(collection.date_created)

def test_model_relationships(self):
    """Test model relationships."""
    collection = Collection.objects.create(
        name="Test Collection",
        creator=self.user
    )
    
    item = CollectableItem.objects.create(
        collection=collection,
        content_id="test-doc-1"
    )
    
    # Test relationship
    self.assertEqual(item.collection, collection)
    self.assertEqual(collection.collectableitem_set.count(), 1)
```

## Common Assertions

```python
# Equality
self.assertEqual(actual, expected)
self.assertNotEqual(actual, unexpected)

# Truth
self.assertTrue(condition)
self.assertFalse(condition)

# Existence
self.assertIsNone(value)
self.assertIsNotNone(value)

# Collections
self.assertIn(item, collection)
self.assertNotIn(item, collection)
self.assertEqual(len(collection), expected_length)

# Strings
self.assertIn("substring", text)
self.assertTrue(text.startswith("prefix"))

# Exceptions
with self.assertRaises(ExceptionType):
    function_that_raises()

# Database queries
self.assertEqual(Model.objects.count(), expected_count)
self.assertTrue(Model.objects.filter(field=value).exists())
```

## Test Data Best Practices

### Creating Test Users

```python
def setUp(self):
    """Create test users with different roles."""
    # Basic user
    self.basic_user = User.objects.create_user(
        username="basic",
        email="basic@example.com",
        password="testpass123"
    )
    
    # Staff user
    self.staff_user = User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="testpass123",
        is_staff=True
    )
    
    # Superuser
    self.admin_user = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="testpass123"
    )
```

### Creating Test Data

```python
def setUp(self):
    """Create test data."""
    # Create groups
    from impresso.signals import create_default_groups
    create_default_groups(sender="impresso")
    
    # Create profile
    from impresso.models import Profile
    self.profile = Profile.objects.create(
        user=self.user,
        uid=f"test-{self.user.username}",
        max_loops_allowed=100
    )
    
    # Create user bitmap
    from impresso.models import UserBitmap
    self.user_bitmap = UserBitmap.objects.create(
        user=self.user
    )
```

## Debugging Tests

### Print Debug Information

```python
def test_with_debug_output(self):
    """Test with debug output."""
    result = function_to_test()
    
    # Print to console for debugging
    print(f"Result: {result}")
    print(f"Mail outbox: {mail.outbox}")
    if mail.outbox:
        print(f"Email body: {mail.outbox[0].body}")
    
    # Your assertions
    self.assertEqual(result, expected)
```

### Using Django Debug Toolbar

The test runner can be configured to show SQL queries:

```python
# In test method
from django.test.utils import override_settings
from django.db import connection

@override_settings(DEBUG=True)
def test_with_query_debugging(self):
    """Test with SQL query debugging."""
    with self.assertNumQueries(expected_query_count):
        function_to_test()
    
    # Print queries
    for query in connection.queries:
        print(query['sql'])
```

## Test Coverage

While not currently enforced, aim for:
- 80%+ code coverage for critical paths
- 100% coverage for security-sensitive code
- Test both success and failure scenarios
- Test edge cases and boundary conditions

## References

- Django Testing Documentation: https://docs.djangoproject.com/en/stable/topics/testing/
- unittest Documentation: https://docs.python.org/3/library/unittest.html
- Django Mail Testing: https://docs.djangoproject.com/en/stable/topics/testing/tools/#email-services
