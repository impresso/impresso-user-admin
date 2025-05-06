import unittest
from django.conf import settings
from impresso.utils.solr import serialize_solr_doc_content_item_to_plain_dict
from impresso.utils.solr import mapper_doc_redact_contents
from impresso.utils.bitmask import BitMask64
from impresso.models.userBitmap import UserBitmap
from typing import Any, Dict


class SolrTestCase(unittest.TestCase):
    """
    run ./manage.py test impresso.tests.test_solr.SolrTestCase
    """

    # def test_JsonWithBitmapDecoder(self):
    #     # Test the JsonWithBitmapDecoder with a valid input
    #     original = '{"bm_get_tr_bin": 0b1010}'
    #     result = json.loads(original, cls=JsonWithBitmapDecoder)

    #     self.assertEqual(result, {"bm_get_tr_bin": "0101"})
    def test_serialize_solr_doc_content_item_to_plain_dict(self) -> None:
        # Test the function with a valid input, a document parsed from solr
        result = serialize_solr_doc_content_item_to_plain_dict(FAKE_SOLR_DOC)

        self.assertEqual(result.get("_" + settings.IMPRESSO_SOLR_FL_TRANSCRIPT_BM), 181)
        self.assertEqual(
            result.get(settings.IMPRESSO_SOLR_FL_TITLE_LABEL), "Subskription."
        )
        self.assertEqual(
            result.get(settings.IMPRESSO_SOLR_FL_CONTENT_LABEL),
            "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
        )
        self.assertEqual(
            result.get(settings.IMPRESSO_SOLR_FL_CONTENT_LENGTH_LABEL), 103
        )
        self.assertEqual(result.get(settings.IMPRESSO_SOLR_FL_COUNTRY_LABEL), "LU")
        self.assertEqual(result.get(settings.IMPRESSO_SOLR_FL_PROVINCE_LABEL), "na")
        self.assertEqual(result.get(settings.IMPRESSO_SOLR_FL_PERIODICITY_LABEL), "na")
        self.assertEqual(result.get(settings.IMPRESSO_SOLR_FL_YEAR_LABEL), 1927)
        self.assertEqual(
            result.get(settings.IMPRESSO_SOLR_FL_MEDIA_CODE_LABEL), "johndoe"
        )
        self.assertEqual(result.get("issue"), "johndoe-1927-11-15-a")
        self.assertEqual(
            result.get(settings.IMPRESSO_SOLR_FL_DATA_PROVIDER_LABEL), "BNL"
        )
        self.assertEqual(
            result.get(settings.IMPRESSO_SOLR_FL_MEDIA_TOPICS_LABEL), "Women"
        )
        self.assertEqual(
            result.get("topics"),
            "tm-de-all-v2.0_tp01_de|0.02 tm-de-all-v2.0_tp03_de|0.166 tm-de-all-v2.0_tp11_de|0.026 ",
        )

    def test_mapper_doc_redact_contents(self):
        doc = serialize_solr_doc_content_item_to_plain_dict(
            {
                "id": "johndoe-1927-11-15-a-i0009",
                "content_txt_de": "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
                "title_txt_de": "Subskription.",
                "meta_year_i": 1927,
                settings.IMPRESSO_SOLR_FL_TRANSCRIPT_BM: 181,
            }
        )
        # Test the function with a valid input, a document parsed from solr
        result_redacted = mapper_doc_redact_contents(
            doc={**doc},
            # not working user bitmask key
            user_bitmask=BitMask64("0000"),
        )
        self.assertEqual(
            result_redacted.get("transcript"),
            settings.IMPRESSO_CONTENT_REDACTED_LABEL,
        )
        self.assertEqual(result_redacted.get("title"), doc.get("title"))

        result_ok = mapper_doc_redact_contents(
            doc={**doc},
            # working user bitmask key
            user_bitmask=BitMask64("1100"),  # 0b10110101
        )
        self.assertEqual(
            result_ok.get("transcript"),
            "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
            "Content is available: the user has a 1 in the right position, the content item is available",
        )

    def test_mapper_get_content_public_domain(self):
        doc = serialize_solr_doc_content_item_to_plain_dict(PUBLIC_DOMAIN_SOLR_DOC)
        # Test the function with a valid input, a document parsed from solr
        result_redacted = mapper_doc_redact_contents(
            doc={**doc},
            # guest user
            user_bitmask=BitMask64(UserBitmap.USER_PLAN_GUEST),
        )
        print(doc)
        print(result_redacted)


FAKE_SOLR_DOC: Dict[str, Any] = {
    "id": "johndoe-1927-11-15-a-i0009",
    "item_type_s": "ar",
    "lg_s": "de",
    "title_txt_fr": "Subskription.",
    "title_txt_de": None,
    "title_txt_en": None,
    "content_txt_fr": None,
    "content_txt_de": "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
    "content_txt_en": None,
    "content_length_i": 103,
    "meta_country_code_s": "LU",
    "meta_province_code_s": "na",
    "meta_periodicity_s": "na",
    "meta_year_i": 1927,
    "meta_journal_s": "johndoe",
    "meta_issue_id_s": "johndoe-1927-11-15-a",
    "meta_partnerid_s": "BNL",
    "meta_topics_s": "Women",
    "meta_polorient_s": "na",
    "olr_b": True,
    "page_id_ss": ["johndoe-1927-11-15-a-p0010"],
    "page_nb_is": [10],
    "nb_pages_i": 1,
    "front_b": False,
    "meta_date_dt": "1927-11-15T00:00:00Z",
    "pers_mentions": None,
    "loc_mentions": None,
    "score": 1.0,
    "exportable_plain": None,
    "topics_dpfs": [
        "tm-de-all-v2.0_tp01_de|0.02 tm-de-all-v2.0_tp03_de|0.166 tm-de-all-v2.0_tp11_de|0.026 "
    ],
    "ucoll_ss": None,
    settings.IMPRESSO_SOLR_FL_COPYRIGHT: "in_cpy",
    settings.IMPRESSO_SOLR_FL_TRANSCRIPT_BM: 181,
}

PUBLIC_DOMAIN_SOLR_DOC: Dict[str, Any] = {
    "id": "BDC-1839-01-20-a-i0003",
    "meta_journal_s": "BDC",
    "meta_year_i": 1839,
    "meta_month_i": 1,
    "meta_yearmonth_s": "1839-01",
    "meta_day_i": 20,
    "meta_ed_s": "a",
    "meta_date_dt": "1839-01-20T00:00:00Z",
    "meta_issue_id_s": "BDC-1839-01-20-a",
    "page_id_ss": ["BDC-1839-01-20-a-p0003"],
    "page_nb_is": [3],
    "nb_pages_i": 1,
    "front_b": False,
    "reading_order_i": 3,
    "meta_country_code_s": "CH",
    "meta_province_code_s": "VS",
    "meta_periodicity_s": "na",
    "meta_topics_s": "Local",
    "meta_polorient_s": "na",
    "meta_partnerid_s": "SNL",
    "rights_data_domain_s": "pbl",
    "rights_copyright_s": "pbl",
    "rights_perm_use_explore_plain": "nur",
    "rights_perm_use_get_tr_plain": "nur",
    "rights_perm_use_get_img_plain": "nur",
    "rights_bm_explore_l": 1,
    "rights_bm_get_tr_l": 1,
    "rights_bm_get_img_l": 1,
    "doc_type_s": "ci",
    "item_type_s": "ar",
    "olr_b": True,
    "lg_orig_s": "fr",
    "lg_s": "fr",
    "content_txt_fr": "SUPPLÉMENTAU SUPPLÉMENTAU BULLETINDESSÉANCES DE LA CONSTITUANTE VALAISANNE m / /«/ woow m / w ",
    "content_length_i": 14,
    "snippet_plain": "SUPPLÉMENTAU SUPPLÉMENTAU BULLETINDESSÉANCES DE LA CONSTITUANTE VALAISANNE m / /«/ woow m / w ",
    "title_txt_fr": "SUPPLÉMENTAU BULLETINDESSÉANCES",
    "pp_plain": '[{"id": "BDC-1839-01-20-a-p0003", "n": 3, "t": [{"c": [330, 54, 281, 35], "s": 0, "l": 12, "hy2": true}, {"c": [455, 100, 33, 23], "s": 13, "l": 12, "hy2": true}, {"c": [29, 141, 887, 57], "s": 26, "l": 18}, {"c": [176, 205, 40, 28], "s": 45, "l": 2}, {"c": [232, 205, 41, 28], "s": 48, "l": 2}, {"c": [288, 205, 249, 28], "s": 51, "l": 12}, {"c": [558, 205, 207, 28], "s": 64, "l": 10}, {"c": [30, 245, 20, 23], "s": 75, "l": 1}, {"c": [50, 245, 8, 23], "s": 77, "l": 1}, {"c": [402, 245, 30, 23], "s": 79, "l": 3}, {"c": [432, 245, 65, 23], "s": 83, "l": 4}, {"c": [685, 245, 20, 23], "s": 88, "l": 1}, {"c": [705, 245, 9, 23], "s": 90, "l": 1}, {"c": [714, 245, 18, 23], "s": 92, "l": 1}], "r": [[30, 41, 884, 144], [176, 207, 586, 20], [30, 251, 44, 12], [380, 251, 132, 12], [686, 251, 48, 12]]}]',
    "rc_plains": [
        "{'pid': 'BDC-1839-01-20-a-p0003', 'c': [[30, 41, 884, 144], [176, 207, 586, 20], [30, 251, 44, 12], [380, 251, 132, 12], [686, 251, 48, 12]]}"
    ],
    "lb_plain": "[10, 15, 44, 74, 78, 87, 93]",
    "pb_plain": "[45, 75, 79, 88]",
    "rb_plain": "[45, 75, 79, 88]",
    "cc_b": True,
}
