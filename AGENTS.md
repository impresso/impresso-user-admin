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
