# GitHub Copilot Agent Configuration

This directory contains configuration files for GitHub Copilot and specialized AI agents.

## Files Overview

### Main Instructions
- **`copilot-instructions.md`** - Main instructions for GitHub Copilot with repository overview, conventions, and guidelines

### Agent-Specific Instructions (`agents/` directory)
- **`celery-tasks.md`** - Guidelines for developing and maintaining Celery background tasks
- **`django-development.md`** - Django application development patterns and best practices
- **`testing.md`** - Testing framework, patterns, and conventions
- **`documentation.md`** - Documentation standards and writing guidelines

## Purpose

These files provide:

1. **Context for AI Assistants** - Help GitHub Copilot and other AI tools understand the codebase structure and conventions
2. **Onboarding Documentation** - Guide new developers on project patterns and practices
3. **Consistency** - Ensure consistent coding style and patterns across the codebase
4. **Best Practices** - Document proven patterns for common tasks

## Usage

### For GitHub Copilot
GitHub Copilot automatically reads `.github/copilot-instructions.md` to understand project conventions.

### For Specialized Agents
Agent-specific instruction files in `.github/agents/` provide detailed guidance for:
- Celery task development with job tracking
- Django models, views, admin interface, and management commands
- Writing comprehensive tests with proper mocking and assertions
- Creating and maintaining project documentation

## Repository Overview

**impresso-user-admin** is a Django application that manages user-related information for the Impresso project. Key features:

- **Background Processing**: Celery with Redis for asynchronous tasks
- **User Management**: Django authentication with custom user plans and permissions
- **Email Notifications**: Multi-format emails (text + HTML) for user actions

## Technology Stack

- Python 3.12+ with type hints
- Django web framework
- Celery task queue with Redis
- MySQL database
- Docker for containerization
- pipenv for dependency management
- mypy for type checking

## Key Concepts

### Task Organization
- **`impresso/tasks/`** - Celery task definitions with decorators
- **`impresso/utils/tasks/`** - Helper functions used by tasks
- Job progress tracking via database and Redis
- User-based permissions

### User Permissions
- User groups for different plans (Basic, Researcher, Educational)
- UserBitmap for fine-grained access control
- Profile with user-specific settings

### Development Workflow
```bash
# Start services
docker compose up -d

# Run Django server
ENV=dev pipenv run ./manage.py runserver

# Run Celery worker (separate terminal)
ENV=dev pipenv run celery -A impresso worker -l info

# Run tests
ENV=dev pipenv run ./manage.py test

# Type checking
pipenv run mypy --config-file ./.mypy.ini impresso
```

## Contributing

When modifying these instruction files:
1. Keep examples practical and based on actual code in the repository
2. Update instructions when significant patterns or conventions change
3. Ensure consistency across all agent instruction files
4. Test that instructions are clear and actionable

## Resources

- Repository: https://github.com/impresso/impresso-user-admin
- Impresso Project: https://impresso-project.ch
- License: GNU Affero General Public License v3.0
