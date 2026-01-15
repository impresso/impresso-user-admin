# Agent: Documentation

This agent specializes in creating and maintaining documentation for the impresso-user-admin project.

## Expertise

- Writing clear and comprehensive README files
- Creating API documentation
- Documenting code with docstrings
- Writing setup and deployment guides
- Creating user guides and tutorials
- Maintaining changelog

## Documentation Standards

### README Structure

A good README should include:

1. **Project Overview** - Brief description of what the project does
2. **Features** - Key features and capabilities
3. **Technology Stack** - Technologies and frameworks used
4. **Installation** - Step-by-step setup instructions
5. **Configuration** - Environment variables and settings
6. **Usage** - How to run and use the application
7. **Development** - Development setup and workflow
8. **Testing** - How to run tests
9. **Deployment** - Production deployment instructions
10. **Contributing** - Guidelines for contributors
11. **License** - License information
12. **Resources** - Links to related resources

### Code Documentation

#### Docstrings

Follow Google-style docstrings for Python:

```python
def function_name(param1: type1, param2: type2) -> return_type:
    """
    Brief description of what the function does.
    
    Longer description if needed, explaining the function's behavior,
    edge cases, and any important implementation details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception is raised
        
    Example:
        >>> result = function_name(value1, value2)
        >>> print(result)
        expected_output
    """
    # Implementation
```

#### Class Documentation

```python
class ClassName:
    """
    Brief description of the class.
    
    Longer description explaining the class's purpose, relationships
    with other classes, and usage patterns.
    
    Attributes:
        attribute1: Description of attribute1
        attribute2: Description of attribute2
        
    Example:
        >>> obj = ClassName(param)
        >>> obj.method()
        expected_output
    """
    
    def __init__(self, param: type):
        """
        Initialize the class.
        
        Args:
            param: Description of initialization parameter
        """
        self.attribute1 = param
```

#### Module Documentation

```python
"""
Module Name

Brief description of what this module does.

This module provides functionality for [purpose]. It includes
classes and functions for [specific capabilities].

Key Components:
    - ClassName: Description
    - function_name: Description

Example:
    Basic usage example:
    
    >>> from module import ClassName
    >>> obj = ClassName()
    >>> result = obj.method()
"""
```

## Django Project Documentation

### Settings Documentation

Document important settings in comments:

```python
# Celery Configuration
# Redis is used as the message broker for Celery task queue
CELERY_BROKER_URL = os.environ.get('REDIS_HOST', 'redis://localhost:6379')

# Maximum number of results returned per Solr query
# This limit prevents excessive resource usage
IMPRESSO_SOLR_EXEC_LIMIT = 100

# Maximum number of query loops allowed per job
# This prevents infinite loops and resource exhaustion
IMPRESSO_SOLR_EXEC_MAX_LOOPS = 100
```

### Model Documentation

```python
class Job(models.Model):
    """
    Tracks the execution of long-running asynchronous tasks.
    
    Jobs are created when a user initiates a long-running operation
    like exporting search results or creating a collection. The job
    status is updated as the task progresses, allowing users to monitor
    progress and cancel if needed.
    
    Status Flow:
        INIT -> RUN -> DONE (success)
        INIT -> RUN -> RIP (stopped/failed)
    """
    
    # Status constants
    INIT = 'init'  # Job created but not started
    RUN = 'run'    # Job is running
    DONE = 'done'  # Job completed successfully
    STOP = 'stop'  # User requested stop
    RIP = 'rip'    # Job stopped or failed
    
    STATUS_CHOICES = [
        (INIT, 'Initialized'),
        (RUN, 'Running'),
        (DONE, 'Done'),
        (STOP, 'Stop Requested'),
        (RIP, 'Stopped'),
    ]
```

### Management Command Documentation

```python
class Command(BaseCommand):
    """
    Export Solr query results to CSV file.
    
    This command executes a Solr query and exports the results to a CSV
    file, respecting user permissions and access controls. The export
    is performed as an asynchronous Celery task with progress tracking.
    
    Usage:
        ENV=dev pipenv run ./manage.py exportqueryascsv USER_ID "QUERY"
        
    Examples:
        # Export French content mentioning "ministre"
        ENV=dev pipenv run ./manage.py exportqueryascsv 1 "content_txt_fr:ministre"
        
        # Export with specific date range
        ENV=dev pipenv run ./manage.py exportqueryascsv 1 "content_txt_fr:* AND date_i:[1900 TO 1950]"
    
    Output:
        Creates a ZIP file containing the CSV export in the user's
        upload directory.
    """
```

## API Documentation

### REST API Endpoints

Document API endpoints with:

- **Method** - HTTP method (GET, POST, PUT, DELETE)
- **URL** - Endpoint URL with parameters
- **Auth** - Authentication requirements
- **Parameters** - Request parameters
- **Response** - Response format and status codes
- **Examples** - Request/response examples

```markdown
### Create Collection

Create a new collection for the authenticated user.

**URL**: `/api/collections/`

**Method**: `POST`

**Auth Required**: Yes

**Permissions**: Authenticated users

**Request Body**:
```json
{
    "name": "My Collection",
    "description": "Collection description"
}
```

**Success Response**:
- **Code**: 201 CREATED
- **Content**:
```json
{
    "id": "user-john-my-collection",
    "name": "My Collection",
    "description": "Collection description",
    "date_created": "2024-01-15T10:30:00Z",
    "creator": {
        "id": 1,
        "username": "john"
    }
}
```

**Error Responses**:
- **Code**: 400 BAD REQUEST
  - **Content**: `{"name": ["This field is required."]}`
- **Code**: 401 UNAUTHORIZED
  - **Content**: `{"detail": "Authentication credentials were not provided."}`

**Example**:
```bash
curl -X POST https://api.example.com/api/collections/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Collection", "description": "Test collection"}'
```
```

## Changelog

Maintain a CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature description

### Changed
- Changed feature description

### Deprecated
- Soon-to-be removed feature

### Removed
- Removed feature

### Fixed
- Bug fix description

### Security
- Security fix description

## [1.0.0] - 2024-01-15

### Added
- Initial release with core features
- User authentication and authorization
- Celery task processing
- Collection management
- Export functionality

[Unreleased]: https://github.com/impresso/impresso-user-admin/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/impresso/impresso-user-admin/releases/tag/v1.0.0
```

## Setup Documentation

### Installation Guide

```markdown
## Installation

### Prerequisites

- Python 3.12+
- pipenv
- Docker and docker-compose
- MySQL 8.0+
- Redis 6.0+

### Step 1: Clone Repository

```bash
git clone https://github.com/impresso/impresso-user-admin.git
cd impresso-user-admin
```

### Step 2: Install Dependencies

```bash
# Install pyenv if not already installed
curl https://pyenv.run | bash

# Install Python version
pyenv install 3.12.4

# Install pipenv
python -m pip install pipenv

# Install project dependencies
pipenv install
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .example.env .dev.env

# Edit .dev.env with your settings
nano .dev.env
```

### Step 4: Start Services

```bash
# Start Redis and MySQL
docker compose up -d

# Run migrations
ENV=dev pipenv run ./manage.py migrate

# Create superuser
ENV=dev pipenv run ./manage.py createsuperuser
```

### Step 5: Run Application

```bash
# Terminal 1: Start Django server
ENV=dev pipenv run ./manage.py runserver

# Terminal 2: Start Celery worker
ENV=dev pipenv run celery -A impresso worker -l info
```

### Step 6: Access Application

- Admin interface: http://localhost:8000/admin/
- Log in with your superuser credentials
```

## Configuration Documentation

### Environment Variables

Document all environment variables:

```markdown
## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key (keep secret!) | `django-insecure-key123...` |
| `DEBUG` | Enable debug mode (only in dev) | `True` |
| `IMPRESSO_DB_HOST` | MySQL database host | `localhost` |
| `IMPRESSO_DB_PORT` | MySQL database port | `3306` |
| `IMPRESSO_DB_NAME` | Database name | `impresso` |
| `IMPRESSO_DB_USER` | Database username | `impresso_user` |
| `IMPRESSO_DB_PASSWORD` | Database password | `secure_password` |
| `REDIS_HOST` | Redis connection URL | `redis://localhost:6379` |

### Solr Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `IMPRESSO_SOLR_URL` | Main Solr index URL | `http://localhost:8983/solr/impresso` |
| `IMPRESSO_SOLR_USER` | Solr read-only user | `reader` |
| `IMPRESSO_SOLR_PASSWORD` | Solr read-only password | `read_password` |
| `IMPRESSO_SOLR_USER_WRITE` | Solr write user | `writer` |
| `IMPRESSO_SOLR_PASSWORD_WRITE` | Solr write password | `write_password` |
| `IMPRESSO_SOLR_PASSAGES_URL` | Text reuse passages index | `http://localhost:8983/solr/passages` |

### Email Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_BACKEND` | Django email backend | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | SMTP server host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP server port | `587` |
| `EMAIL_USE_TLS` | Use TLS encryption | `True` |
| `EMAIL_HOST_USER` | SMTP username | `user@example.com` |
| `EMAIL_HOST_PASSWORD` | SMTP password | `app_password` |
| `DEFAULT_FROM_EMAIL` | Default sender email | `noreply@impresso-project.ch` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `IMPRESSO_SOLR_EXEC_LIMIT` | Max rows per Solr query | `100` | `200` |
| `IMPRESSO_SOLR_EXEC_MAX_LOOPS` | Max query loops | `100` | `200` |
| `IMPRESSO_BASE_URL` | Base URL for links | - | `https://impresso-project.ch` |
```

## Troubleshooting Documentation

```markdown
## Troubleshooting

### Common Issues

#### Database Connection Errors

**Problem**: `django.db.utils.OperationalError: (2003, "Can't connect to MySQL server")`

**Solution**:
1. Check MySQL is running: `docker ps`
2. Verify connection settings in `.dev.env`
3. Test connection: `mysql -h localhost -u user -p`

#### Redis Connection Errors

**Problem**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solution**:
1. Check Redis is running: `docker ps`
2. Test connection: `redis-cli ping`
3. Verify `REDIS_HOST` in `.dev.env`

#### Celery Tasks Not Processing

**Problem**: Tasks are queued but not executed

**Solution**:
1. Check Celery worker is running
2. Check Redis connection
3. Verify task is registered: `pipenv run celery -A impresso inspect registered`
4. Check worker logs for errors

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'xyz'`

**Solution**:
1. Ensure you're in pipenv shell: `pipenv shell`
2. Install dependencies: `pipenv install`
3. Check Python version: `python --version`

### Debug Mode

Enable verbose logging:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
```
```

## Testing Documentation

Document how to run and write tests:

```markdown
## Testing

### Running Tests

```bash
# Run all tests
ENV=dev pipenv run ./manage.py test

# Run specific test module
ENV=dev pipenv run ./manage.py test impresso.tests.utils.tasks.test_account

# Run with coverage
ENV=dev pipenv run coverage run --source='impresso' manage.py test
ENV=dev pipenv run coverage report
ENV=dev pipenv run coverage html

# Run with verbose output
ENV=dev pipenv run ./manage.py test --verbosity=2
```

### Writing Tests

See `.github/agents/testing.md` for comprehensive testing guidelines.

### Test Structure

Tests are organized to mirror the application structure:

```
impresso/tests/
├── models/           # Model tests
├── tasks/            # Task tests
├── utils/
│   └── tasks/        # Task utility tests
└── views/            # View tests
```
```

## Deployment Documentation

```markdown
## Deployment

### Production Setup

#### Prerequisites

- Docker installed on production server
- SSL certificate configured
- Domain name configured
- Firewall rules configured

#### Step 1: Prepare Environment

```bash
# Create production environment file
cp .example.env .prod.env

# Edit with production values
nano .prod.env

# Important: Set DEBUG=False
# Important: Set strong SECRET_KEY
# Important: Configure ALLOWED_HOSTS
```

#### Step 2: Build Docker Image

```bash
# Build image
make build BUILD_TAG=v1.0.0

# Test image locally
make run BUILD_TAG=v1.0.0
```

#### Step 3: Deploy

```bash
# Push image to registry
docker tag impresso/impresso-user-admin:v1.0.0 registry.example.com/impresso-user-admin:v1.0.0
docker push registry.example.com/impresso-user-admin:v1.0.0

# On production server
docker pull registry.example.com/impresso-user-admin:v1.0.0
docker-compose up -d
```

#### Step 4: Run Migrations

```bash
docker-compose exec web python manage.py migrate
```

#### Step 5: Collect Static Files

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Monitoring

- Check logs: `docker-compose logs -f web`
- Check Celery: `docker-compose logs -f celery`
- Monitor Redis: `redis-cli info`
- Monitor MySQL: Check database connections

### Backup

```bash
# Backup database
docker-compose exec db mysqldump -u user -p database > backup.sql

# Backup media files
tar -czf media_backup.tar.gz media/
```
```

## Contributing Guidelines

```markdown
## Contributing

We welcome contributions! Please follow these guidelines:

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Write or update tests
5. Run tests: `ENV=dev pipenv run ./manage.py test`
6. Run type checking: `pipenv run mypy impresso`
7. Commit changes: `git commit -m "Add my feature"`
8. Push to branch: `git push origin feature/my-feature`
9. Create Pull Request

### Code Style

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for all public functions/classes
- Keep functions small and focused
- Write descriptive commit messages

### Testing

- Write tests for all new features
- Maintain test coverage above 80%
- Test both success and error cases
- Use meaningful test names

### Documentation

- Update README for new features
- Add docstrings to new code
- Update API documentation if applicable
- Update CHANGELOG.md
```

## References

- [Write the Docs](https://www.writethedocs.org/)
- [Google Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Django Documentation](https://docs.djangoproject.com/)
