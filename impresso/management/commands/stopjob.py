from django.core.management.base import BaseCommand
from impresso.models import Job


class Command(BaseCommand):
    help = 'stop manually a running job'

    def add_arguments(self, parser):
        parser.add_argument('job_ids', nargs='+', type=str)

    def handle(self, job_ids, *args, **options):
        self.stdout.write(f'stop: {job_ids}')
        jobs = Job.objects.filter(pk__in=job_ids)
        self.stdout.write(f'n. jobs to stop: {jobs.count()}')
        for job in jobs:
            job.status = Job.STOP
            job.save()
            self.stdout.write(f'job {job.pk} saved, extra={job.extra}')
