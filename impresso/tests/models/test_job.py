import json
from django.test import TestCase
from django.contrib.auth.models import User
from ...models import Job, Profile
from ...utils.tasks import TASKSTATE_PROGRESS, update_job_progress
from ...utils.tasks import TASKSTATE_SUCCESS, update_job_completed


class FakeTask:
    type = Job.TEST
    name = "Fake Task"

    def update_state(self, state, meta):
        pass


class JobTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.profile = Profile.objects.create(user=self.user, uid="local-testuser")
        # thsi is normally created directly inside the main celery task
        # to be tested in a specific test_tasks.py file
        self.job = Job.objects.create(
            type=Job.TEST, status=Job.READY, creator=self.user
        )

        self.task = FakeTask()

    def test_job_extra_after_task_init(self):
        # create a very fake celery task instance
        # use the task to update the job progress
        update_job_progress(
            task=self.task,
            job=self.job,
            taskstate=TASKSTATE_PROGRESS,
            progress=0.1,
            message="Task is initialising",
            logger=None,
        )
        # get the job extra field as a dictionary from textfield
        task_meta = json.loads(self.job.extra)
        # print(self.job.extra)
        # # assert: {"task": "TES", "taskname": "Fake Task", "progress": 0.5, "job_type": "TES", "job_status": "REA", "job_date_created": "2024-11-11T07:07:27.141484+00:00", "user_id": 1, "user_uid": self.profile.uid}
        # self.assertEqual(
        #     self.job.extra,
        #     '{"task": "TES", "taskname": "Fake Task", "progress": 0.5, "job_type": "TES", "job_status": "REA", "job_date_created": "2024-11-11T07:07:27.141484+00:00", "user_id": 1, "user_uid": self.profile.uid}'
        # )
        self.assertEqual(task_meta["task"], "TES")
        self.assertEqual(task_meta["taskname"], "Fake Task")
        self.assertEqual(task_meta["progress"], 0.1)
        self.assertEqual(task_meta["job_type"], "TES")
        self.assertEqual(task_meta["job_status"], Job.READY)
        self.assertEqual(task_meta["user_id"], self.user.pk)
        self.assertEqual(task_meta["user_uid"], self.profile.uid)
        self.assertEqual(task_meta["message"], "Task is initialising")

        # let's simulate progress task
        self.job.status = Job.RUN
        update_job_progress(
            task=self.task,
            job=self.job,
            taskstate=TASKSTATE_PROGRESS,
            progress=0.5,
            message="Task is progressing",
            logger=None,
        )
        task_meta = json.loads(self.job.extra)
        # {"task": "TES", "taskname": "Fake Task", "progress": 0.5, "job_type": "TES", "job_status": "RUN", "job_date_created": "2024-11-11T07:07:27.141484+00:00", "user_id": 1, "user_uid": self.profile.uid}
        self.assertEqual(task_meta["task"], "TES")
        self.assertEqual(task_meta["taskname"], "Fake Task")
        self.assertEqual(task_meta["progress"], 0.5)
        self.assertEqual(task_meta["job_type"], "TES")
        self.assertEqual(task_meta["job_status"], Job.RUN)
        self.assertEqual(task_meta["user_id"], self.user.pk)
        self.assertEqual(task_meta["user_uid"], self.profile.uid)
        self.assertEqual(task_meta["message"], "Task is progressing")

    def test_job_extra_after_task_complete(self):
        update_job_completed(
            task=self.task,
            job=self.job,
        )
        task_meta = json.loads(self.job.extra)
        # {"task": "TES", "taskname": "Fake Task", "progress": 1.0, "job_type": "TES", "job_status": "DON", "job_date_created": "2024-11-11T07:15:49.422087+00:00", "user_id": 1, "user_uid": self.profile.uid}
        self.assertEqual(task_meta["task"], "TES")
        self.assertEqual(task_meta["taskname"], "Fake Task")
        self.assertEqual(task_meta["progress"], 1.0)
        self.assertEqual(task_meta["job_type"], "TES")
        self.assertEqual(task_meta["job_status"], Job.DONE)
        self.assertEqual(task_meta["user_id"], self.user.pk)
