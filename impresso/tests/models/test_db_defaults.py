from django.db import connection, models
from django.test import SimpleTestCase, TransactionTestCase

from impresso.models import (
    CollectableItem,
    Collection,
    Job,
    Page,
    Profile,
    SearchQuery,
    SpecialMembershipDataset,
    Tag,
    UploadedImage,
    UserChangePlanRequest,
    UserSpecialMembershipRequest,
)


class ModelDatabaseDefaultsTest(SimpleTestCase):
    def test_scalar_defaults_match_python_and_database(self):
        defaults = {
            Collection: {"count_items": 0},
            Tag: {"count_items": 0},
            CollectableItem: {"indexed": False, "search_query_score": 0.0},
            Job: {"status": Job.READY},
            Page: {"is_corrupted": False, "is_converted": False, "n_tokens": 0, "ocr_quality": 0.0},
            Profile: {
                "provider": Profile.PROVIDER_LOCAL,
                "email_accepted": False,
                "email_verified": False,
                "max_loops_allowed": 100,
                "max_parallel_jobs": 2,
            },
            SearchQuery: {"count_items": 0},
            UserChangePlanRequest: {"status": UserChangePlanRequest.STATUS_PENDING},
            UserSpecialMembershipRequest: {"status": UserSpecialMembershipRequest.STATUS_PENDING},
        }
        for model, fields in defaults.items():
            instance = model()
            for name, expected in fields.items():
                with self.subTest(model=model.__name__, field=name):
                    field = model._meta.get_field(name)
                    self.assertEqual(getattr(instance, name), expected)
                    self.assertEqual(field.db_default, expected)

    def test_non_scalar_defaults_remain_python_only_and_documented(self):
        fields = (
            (Job, "extra"),
            (Job, "description"),
            (UploadedImage, "thumbnail"),
            (SpecialMembershipDataset, "metadata"),
            (UserChangePlanRequest, "changelog"),
            (UserSpecialMembershipRequest, "changelog"),
            (Job, "date_created"),
            (Job, "date_last_modified"),
        )
        for model, name in fields:
            with self.subTest(model=model.__name__, field=name):
                field = model._meta.get_field(name)
                self.assertFalse(field.has_db_default())
                self.assertTrue(field.db_comment)


class RawDatabaseDefaultsTest(TransactionTestCase):
    def test_raw_insert_uses_database_defaults(self):
        class DefaultsProbe(models.Model):
            provider = Profile._meta.get_field("provider").clone()
            email_verified = Profile._meta.get_field("email_verified").clone()
            max_parallel_jobs = Profile._meta.get_field("max_parallel_jobs").clone()
            search_query_score = CollectableItem._meta.get_field("search_query_score").clone()

            class Meta:
                app_label = "impresso"
                db_table = "test_database_defaults_probe"

        with connection.schema_editor() as editor:
            editor.create_model(DefaultsProbe)
        try:
            with connection.cursor() as cursor:
                table = connection.ops.quote_name(DefaultsProbe._meta.db_table)
                cursor.execute(f"INSERT INTO {table} (id) VALUES (%s)", [1])
            row = DefaultsProbe.objects.get(pk=1)
            self.assertEqual(row.provider, Profile.PROVIDER_LOCAL)
            self.assertIs(row.email_verified, False)
            self.assertEqual(row.max_parallel_jobs, 2)
            self.assertEqual(row.search_query_score, 0.0)
        finally:
            with connection.schema_editor() as editor:
                editor.delete_model(DefaultsProbe)
