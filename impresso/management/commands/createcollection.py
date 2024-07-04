from django.core.management.base import BaseCommand
from impresso.models import Collection
from django.contrib.auth.models import User
from django.utils.text import slugify


class Command(BaseCommand):
    help = "Create an empty collection for a user."

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)
        parser.add_argument("username", type=str)

    def handle(self, username, name, *args, **options):
        self.stdout.write("---\n")
        self.stdout.write(f'ARG username: "{username}"')
        self.stdout.write(f'ARG name: "{name}"')
        creator = User.objects.get(username=username)
        collection, created = Collection.objects.get_or_create(
            id=f"{creator.profile.uid}_{slugify(name)}",
            name=name,
            creator=creator,
        )
        self.stdout.write(f"collection.id: \033[1m\033[34m{collection.id}\033[0m")
        self.stdout.write(f"collection.name: {collection.name}")
        self.stdout.write(f"created {collection.date_created}")
        self.stdout.write(f"created NOW: {created}")
        self.stdout.write(f"creator: {collection.creator.username}")
        self.stdout.write("SUCCESS! ❤️ \n---\n")
