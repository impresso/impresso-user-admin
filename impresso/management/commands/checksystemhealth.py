import re
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

FLS = [
    "id",
    "content_length_i",
    "snippet_plain",
    "bm_explore_s",
    "bm_get_tr_s",
    "bm_get_img_s",
    "meta_journal_s",
    "meta_partnerid_s",
]


class Command(BaseCommand):
    help = "Check SOLR connectivity"

    def handle(self, *args, **options):
        self.stdout.write("Checking Database connectivity...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            database_name = cursor.fetchone()[0]

            self.stdout.write(
                f"Current Database: \n   \033[94m{database_name}\033[0m\n\n"
            )
            cursor.execute("SHOW TABLES")
            tables = [t[0] for t in cursor.fetchall()]
            self.stdout.write(f"Database Tables: \n - {'\n - '.join(tables)}")

        # test solr connectivity usin g settings
        self.stdout.write("\nChecking SOLR connectivity...")
        solr_url = settings.IMPRESSO_SOLR_URL_SELECT
        # check that solr_url is following the regex pattern, without select at the end
        # https://<host>:<port>/solr/<collection>/select
        if not re.match(r"^https?://.*\/solr/[^\/]+\/select$", solr_url):
            self.stderr.write(f"Invalid SOLR URL: {solr_url}")
            return

        params = {
            "q": "*:*",
            "rows": 2,
            "fl": ",".join(FLS),
        }
        solr_response = requests.get(
            solr_url,
            auth=settings.IMPRESSO_SOLR_AUTH,
            params=params,
        )
        solr_status = solr_response.status_code
        self.stdout.write(f"SOLR URL: \n - {solr_url}")
        self.stdout.write(f"SOLR Status: \n - {solr_status}")
        # n of rows in solr
        solr_num_rows = solr_response.json()["response"]["numFound"]
        self.stdout.write(f"SOLR Num Rows: \n - {solr_num_rows}")
        # example result
        docs = solr_response.json()["response"]["docs"]
        self.stdout.write(f"\n SOLR Example Docs:")

        for doc in docs:
            self.stdout.write(f" - \nid:\033[94m{doc.get('id')}\033[0m")

            for field in FLS:
                self.stdout.write(f"  {field}: {doc.get(field)}")
        # ping redis
        self.stdout.write("\nChecking Redis connectivity...")
        import redis

        redis_host = settings.REDIS_HOST.split(":")[0]
        redis_port = settings.REDIS_HOST.split(":")[-1]
        # if redis_port it is not numeric, then throw an error
        if not redis_port.isnumeric():
            self.stderr.write(f"Invalid Redis Port: {redis_port}")
            return
        self.stdout.write(f"Redis Host: \n - {redis_host}")
        self.stdout.write(f"Redis Port: \n - {redis_port}")

        redis_conn = redis.Redis(host=redis_host, port=redis_port, db="4")
        redis_status = redis_conn.ping()
        self.stdout.write(f"Redis Status: \n - {redis_status}")
