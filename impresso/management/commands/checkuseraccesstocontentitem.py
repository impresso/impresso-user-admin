from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...utils.bitmask import BitMask64, is_access_allowed
from impresso.solr import find_all

ci_fields_to_display = [
    "id",
    "snippet_plain",
    "rights_copyright_s",
    "rights_perm_use_explore_plain",
    "rights_bm_explore_l",
    "rights_data_domain_s",
    "rights_copyright_s",
    "rights_perm_use_explore_plain",
    "rights_perm_use_get_tr_plain",
    "rights_perm_use_get_img_plain",
    "rights_bm_explore_l",
    "rights_bm_get_tr_l",
    "rights_bm_get_img_l",
]


def encode_bitmap_str2int_solr_b2(bitmap: str) -> int:
    return int(bitmap[::-1], 2)  # Reverse and convert to integer base 2


class Command(BaseCommand):
    help = "Test a user bitmap against a content bitmap"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("contentItemId", type=str)

    def handle(self, username, contentItemId, *args, **options):
        self.stdout.write(f"Get user with username: {username}")
        user = User.objects.get(username=username)
        self.stdout.write(f"User: pk={user.id} \033[34m{user.username}\033[0m")
        user_bitmask = BitMask64(user.bitmap.bitmap)
        self.stdout.write(f"Get content item with id: {contentItemId}")
        solr_response_data = find_all(
            q=f"id:{contentItemId}",
            fl=",".join(ci_fields_to_display),
            limit=1,
            skip=0,
        )
        content_item = solr_response_data.get("response", {}).get("docs", [])[0]

        for field in ci_fields_to_display:
            if field not in content_item:
                self.stdout.write(
                    f"Field \033[31m{field}\033[0m not found in content item."
                )
                continue
            self.stdout.write(f"{field}: \033[34m{content_item.get(field)}\033[0m")

        rights_keys = [
            "rights_bm_explore_l",
            "rights_bm_get_tr_l",
            "rights_bm_get_img_l",
        ]

        self.stdout.write(f"user BitMask64:\n \033[34m{str(user_bitmask)}\033[0m")

        for key in rights_keys:
            content_bitmask = BitMask64(content_item.get(key))
            access_allowed = is_access_allowed(user_bitmask, content_bitmask)

            self.stdout.write(
                f"\ncontent \033[1m{key}\033[0m BitMask64:\n \033[34m{str(content_bitmask)}\033[0m"
            )
            self.stdout.write(
                f" int value (check):\n {encode_bitmap_str2int_solr_b2(str(content_bitmask)[::-1])}"
            )
            if access_allowed:
                self.stdout.write(self.style.SUCCESS(f" User has access to {key}"))
            else:
                self.stdout.write(self.style.ERROR(f" user access denied to {key}"))

        self.stdout.write("\n---\nDone! \033[31m❤️\033[0m \n---\n")
