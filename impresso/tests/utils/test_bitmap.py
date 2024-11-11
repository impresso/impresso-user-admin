import unittest
from ..test_solr import FAKE_SOLR_DOC
from impresso.solr import serialize_solr_doc_content_item_to_plain_dict
from impresso.utils.solr import mapper_doc_redact_contents
from impresso.utils.bitmap import check_bitmap_keys_overlap


class BitmapTestCase(unittest.TestCase):
    """
    Run the test with:
    pipenv run ./manage.py test ./impresso/tests/utils/tasks
    """

    def test_check_bitmap_keys_overlap(self):
        self.assertTrue(
            check_bitmap_keys_overlap("10000", "1"),
            "Content is available, even if the user is not authentified: the content item is available in public domain",
        )

        self.assertFalse(
            check_bitmap_keys_overlap("10000", "01"),
            "Content is not available: the user is not authentified, the content item is available only to authentified users",
        )

        self.assertTrue(
            check_bitmap_keys_overlap("11000", "01"),
            "Content is available: the user is authentified, the content item is available only to authentified users",
        )
        # now with integers
        self.assertTrue(
            check_bitmap_keys_overlap("010001", 0b100000),
            f"Content is available: the user has a package in the right spot, the content item is available",
        )
        self.assertFalse(
            check_bitmap_keys_overlap("010001", 0b1000000),
            f"Content is NOT available: the user has a package in wrong bit position, the content item is not available",
        )
        self.assertTrue(
            check_bitmap_keys_overlap("0011", 0b100),
            f"Content is available: the user has a academic power",
        )
        self.assertFalse(
            check_bitmap_keys_overlap("0010", 0b1000),
            f"Content is NOT available: the user has a student power, content item is for academics only",
        )

    def test_mapper_doc_redact_contents(self):
        doc = serialize_solr_doc_content_item_to_plain_dict(
            {
                "id": "johndoe-1927-11-15-a-i0009",
                "content_txt_de": "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
                "title_txt_de": "Subskription.",
                "meta_year_i": 1927,
                "bm_get_tr_i": 181,
            }
        )

        # Test the function with a valid input, a document parsed from solr
        result_redacted = mapper_doc_redact_contents(
            doc={**doc},
            # not working user bitmask key
            user_bitmap_key="0000",
        )
        self.assertEqual(result_redacted.get("content"), "[redacted]")
        self.assertEqual(result_redacted.get("title"), doc.get("title"))

        result_ok = mapper_doc_redact_contents(
            doc={**doc},
            # working user bitmask key
            user_bitmap_key="1100",  # 0b10110101
        )
        self.assertEqual(
            result_ok.get("content"),
            "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
            "Content is available: the user has a 1 in the right position, the content item is available",
        )
