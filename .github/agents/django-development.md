# Agent: Django Development

This agent specializes in Django application development for the impresso-user-admin project.

## Expertise

- Django models, views, and admin interface
- User authentication and authorization
- Django signals and middleware
- URL routing and template rendering
- Django management commands
- Database migrations
- Form handling and validation

## Django Project Structure

### Apps Organization

The project is organized as a single Django app named `impresso` with the following structure:

```
impresso/
├── __init__.py
├── settings.py              # Django settings
├── base.py                  # Base settings and dotenv loading
├── urls.py                  # URL routing
├── wsgi.py                  # WSGI application
├── celery.py                # Celery configuration
├── models/                  # Database models
├── views/                   # View functions/classes
├── admin/                   # Admin customizations
├── signals.py               # Django signals
├── management/
│   └── commands/            # Custom management commands
├── templates/               # HTML templates
│   └── emails/              # Email templates
├── static/                  # Static files (CSS, JS, images)
└── tests/                   # Test suite
```

## Models

### Model Conventions

- Use `django.db.models.Model` as base class
- Define `__str__()` method for readable representations
- Use `Meta` class for model options
- Add docstrings to models and complex fields
- Use Django's built-in field types
- Define proper relationships (ForeignKey, ManyToMany)

### Key Models

- **User** - Django's built-in User model (from `django.contrib.auth.models`)
- **Profile** - User profile with `uid` and `max_loops_allowed`
- **UserBitmap** - User access permissions as bitmap
- **Job** - Tracks asynchronous background tasks
- **Collection** - User-created collections of content items
- **CollectableItem** - Items within collections
- **UserChangePlanRequest** - Plan upgrade/downgrade requests
- **UserSpecialMembershipRequest** - Special membership requests

### Model Example

```python
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class MyModel(models.Model):
    """
    Description of the model.
    """
    # Fields
    name = models.CharField(max_length=255, help_text="Display name")
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mymodels"
    )
    date_created = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_created']
        verbose_name = "My Model"
        verbose_name_plural = "My Models"
        indexes = [
            models.Index(fields=['creator', '-date_created']),
        ]
    
    def __str__(self):
        return f"{self.name} (by {self.creator.username})"
    
    def save(self, *args, **kwargs):
        """Override save to add custom logic."""
        # Custom logic before save
        super().save(*args, **kwargs)
        # Custom logic after save
```

## Django Admin

### Admin Customization

Customize the admin interface in `impresso/admin/`:

```python
from django.contrib import admin
from impresso.models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    """Admin interface for MyModel."""
    
    list_display = ('name', 'creator', 'date_created', 'is_active')
    list_filter = ('is_active', 'date_created')
    search_fields = ('name', 'creator__username')
    readonly_fields = ('date_created',)
    date_hierarchy = 'date_created'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'creator', 'is_active')
        }),
        ('Metadata', {
            'fields': ('date_created',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('creator')
```

### Admin Actions

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    actions = ['activate_items', 'deactivate_items']
    
    def activate_items(self, request, queryset):
        """Activate selected items."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} items activated.")
    activate_items.short_description = "Activate selected items"
    
    def deactivate_items(self, request, queryset):
        """Deactivate selected items."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} items deactivated.")
    deactivate_items.short_description = "Deactivate selected items"
```

## Management Commands

### Creating Management Commands

Create custom commands in `impresso/management/commands/`:

```python
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from impresso.models import MyModel
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command description.
    
    Usage:
        ENV=dev pipenv run ./manage.py mycommand [options]
    """
    help = 'Command description'
    
    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            'user_id',
            type=int,
            help='User ID to process'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        """Execute command logic."""
        user_id = options['user_id']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # Set logging level
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        try:
            user = User.objects.get(pk=user_id)
            logger.info(f"Processing user: {user.username}")
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('DRY RUN - no changes made')
                )
            else:
                # Do actual work
                result = self.process_user(user)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully processed: {result}')
                )
        
        except User.DoesNotExist:
            raise CommandError(f'User with ID {user_id} does not exist')
        
        except Exception as e:
            logger.exception(f"Error processing user {user_id}")
            raise CommandError(f'Error: {e}')
    
    def process_user(self, user):
        """Process user logic."""
        # Implementation
        return "result"
```

### Existing Commands

Key management commands in the project:

- `createaccount` - Create user accounts with random passwords
- `createsuperuser` - Create admin user (built-in Django command)
- `synccollection` - Sync a collection to Solr index
- `exportqueryascsv` - Export Solr query results as CSV
- `createcollection` - Create or get a collection
- `addtocollectionfromquery` - Add query results to collection
- `addtocollectionfromtrpassagesquery` - Add TR passages to collection
- `stopjob` - Stop a running job

## Settings Management

### Environment-Based Settings

Settings are loaded via dotenv files:

```python
# impresso/base.py
import os
from dotenv import load_dotenv

# Load environment-specific .env file
env = os.environ.get('ENV', 'dev')
env_file = f'.{env}.env' if env != 'dev' else '.env'
load_dotenv(env_file)

# Access settings
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
```

### Settings Structure

- `impresso/base.py` - Base settings and dotenv loading
- `impresso/settings.py` - Main settings file
- `.example.env` - Template for environment variables
- `.dev.env` - Development settings
- `.prod.env` - Production settings

### Key Settings

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': os.environ.get('IMPRESSO_DB_HOST'),
        'PORT': os.environ.get('IMPRESSO_DB_PORT'),
        'NAME': os.environ.get('IMPRESSO_DB_NAME'),
        'USER': os.environ.get('IMPRESSO_DB_USER'),
        'PASSWORD': os.environ.get('IMPRESSO_DB_PASSWORD'),
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get('REDIS_HOST', 'redis://localhost:6379')

# Email
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

# Solr
IMPRESSO_SOLR_URL = os.environ.get('IMPRESSO_SOLR_URL')
IMPRESSO_SOLR_USER = os.environ.get('IMPRESSO_SOLR_USER')
IMPRESSO_SOLR_PASSWORD = os.environ.get('IMPRESSO_SOLR_PASSWORD')

# Custom settings
IMPRESSO_BASE_URL = os.environ.get('IMPRESSO_BASE_URL')
IMPRESSO_SOLR_EXEC_LIMIT = 100
IMPRESSO_SOLR_EXEC_MAX_LOOPS = 100
```

## Django Signals

### Signal Definitions

Signals are defined in `impresso/signals.py`:

```python
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from impresso.models import Profile, UserBitmap

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create Profile and UserBitmap when User is created.
    """
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={'uid': f"user-{instance.username}"}
        )
        UserBitmap.objects.get_or_create(user=instance)

@receiver(pre_save, sender=UserBitmap)
def update_user_bitmap(sender, instance, **kwargs):
    """
    Update bitmap before saving based on user groups.
    """
    # Calculate bitmap value from user groups
    instance.calculate_bitmap()
```

### Signal Registration

Signals must be imported in `impresso/__init__.py`:

```python
default_app_config = 'impresso.apps.ImpressoConfig'
```

And in `impresso/apps.py`:

```python
from django.apps import AppConfig

class ImpressoConfig(AppConfig):
    name = 'impresso'
    
    def ready(self):
        """Import signals when app is ready."""
        import impresso.signals
```

## User Authentication & Authorization

### User Groups

The project uses Django groups for user plans:

- `settings.IMPRESSO_GROUP_USER_PLAN_BASIC` - Basic user plan
- `settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER` - Researcher plan
- `settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL` - Educational plan
- `settings.IMPRESSO_GROUP_USER_PLAN_NO_REDACTION` - Special privilege

### Checking User Permissions

```python
from django.conf import settings

def check_user_plan(user):
    """Check user's plan."""
    if user.groups.filter(name=settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER).exists():
        return 'researcher'
    elif user.groups.filter(name=settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL).exists():
        return 'educational'
    else:
        return 'basic'

def user_has_no_redaction(user):
    """Check if user has no-redaction privilege."""
    return user.groups.filter(
        name=settings.IMPRESSO_GROUP_USER_PLAN_NO_REDACTION
    ).exists()
```

### User Profile Access

```python
def get_user_limits(user):
    """Get user's execution limits."""
    profile = user.profile
    return {
        'max_loops': min(
            profile.max_loops_allowed,
            settings.IMPRESSO_SOLR_EXEC_MAX_LOOPS
        ),
        'uid': profile.uid,
    }
```

## Database Migrations

### Creating Migrations

```bash
# Create migrations for changes
ENV=dev pipenv run ./manage.py makemigrations

# Create named migration
ENV=dev pipenv run ./manage.py makemigrations --name add_field_to_model

# Show SQL for migrations
ENV=dev pipenv run ./manage.py sqlmigrate impresso 0001

# Apply migrations
ENV=dev pipenv run ./manage.py migrate

# Show migration status
ENV=dev pipenv run ./manage.py showmigrations
```

### Migration Best Practices

- Keep migrations small and focused
- Test migrations on copy of production data
- Never modify applied migrations
- Use `RunPython` for data migrations
- Add `reverse_code` for rollback support

### Data Migration Example

```python
from django.db import migrations

def forwards_func(apps, schema_editor):
    """Apply data migration."""
    MyModel = apps.get_model('impresso', 'MyModel')
    db_alias = schema_editor.connection.alias
    
    # Update data
    MyModel.objects.using(db_alias).filter(
        old_field=True
    ).update(new_field='value')

def reverse_func(apps, schema_editor):
    """Reverse data migration."""
    MyModel = apps.get_model('impresso', 'MyModel')
    db_alias = schema_editor.connection.alias
    
    # Reverse changes
    MyModel.objects.using(db_alias).filter(
        new_field='value'
    ).update(old_field=True)

class Migration(migrations.Migration):
    dependencies = [
        ('impresso', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
```

## URL Configuration

URLs are defined in `impresso/urls.py`:

```python
from django.urls import path, include
from django.contrib import admin
from impresso import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('impresso.api.urls')),
    path('accounts/', include('django_registration.backends.activation.urls')),
]
```

## Templates

### Template Organization

Templates are in `impresso/templates/`:

```
templates/
├── base.html                # Base template
├── emails/                  # Email templates
│   ├── notification.txt     # Plain text version
│   └── notification.html    # HTML version
└── admin/                   # Admin overrides
```

### Email Templates

Email templates should have both .txt and .html versions:

```html
<!-- emails/notification.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body>
    <p>Dear {{ user.first_name }},</p>
    <p>{{ message }}</p>
    <p>Best regards,<br>The Impresso Team</p>
</body>
</html>
```

```text
# emails/notification.txt
Dear {{ user.first_name }},

{{ message }}

Best regards,
The Impresso Team
```

## Middleware

Custom middleware can be added to `impresso/middleware.py`:

```python
class CustomMiddleware:
    """Custom middleware description."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Code executed before view
        
        response = self.get_response(request)
        
        # Code executed after view
        
        return response
```

Register in settings:

```python
MIDDLEWARE = [
    # Django defaults
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ...
    'impresso.middleware.CustomMiddleware',  # Add custom middleware
]
```

## Database Optimization

### Query Optimization

```python
# Use select_related for ForeignKey
users = User.objects.select_related('profile').all()

# Use prefetch_related for ManyToMany
users = User.objects.prefetch_related('groups').all()

# Use only() to fetch specific fields
users = User.objects.only('id', 'username', 'email').all()

# Use defer() to exclude fields
users = User.objects.defer('password', 'last_login').all()

# Use exists() instead of count() for existence check
if User.objects.filter(email=email).exists():
    # ...

# Use values() for dictionary results
user_data = User.objects.values('id', 'username', 'email')
```

### Database Transactions

```python
from django.db import transaction

# Atomic decorator
@transaction.atomic
def create_user_with_profile(username, email):
    """Create user and profile atomically."""
    user = User.objects.create_user(username=username, email=email)
    Profile.objects.create(user=user, uid=f"user-{username}")
    return user

# Context manager
def update_user_plan(user, plan):
    """Update user plan atomically."""
    with transaction.atomic():
        user.groups.clear()
        user.groups.add(plan)
        user.profile.plan_updated = timezone.now()
        user.profile.save()
```

## Logging

Configure logging in settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'impresso': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

## Security Best Practices

- Use Django's built-in security features
- Never store plaintext passwords
- Use CSRF protection for forms
- Validate and sanitize all user inputs
- Use Django's ORM to prevent SQL injection
- Keep SECRET_KEY secret and unique
- Use HTTPS in production
- Regularly update dependencies

## References

- Django Documentation: https://docs.djangoproject.com/
- Django Admin: https://docs.djangoproject.com/en/stable/ref/contrib/admin/
- Django Management Commands: https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
- Django Migrations: https://docs.djangoproject.com/en/stable/topics/migrations/
- Django Signals: https://docs.djangoproject.com/en/stable/topics/signals/
