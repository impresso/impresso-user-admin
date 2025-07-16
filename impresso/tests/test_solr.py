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

        self.assertEqual(
            result_redacted[settings.IMPRESSO_SOLR_FL_CONTENT_LABEL],
            doc[settings.IMPRESSO_SOLR_FL_CONTENT_LABEL],
            "Content is available as it is Public Domain",
        )
        self.assertEqual(
            result_redacted[settings.IMPRESSO_SOLR_FL_TITLE_LABEL],
            doc[settings.IMPRESSO_SOLR_FL_TITLE_LABEL],
            "Title is available: it is metadata",
        )

    def test_mapper_get_content_protected(self):
        doc = serialize_solr_doc_content_item_to_plain_dict(PROTECTED_SOLR_DOC)
        # Test the function with a valid input, a document parsed from solr
        result_redacted = mapper_doc_redact_contents(
            doc={**doc},
            # guest user
            user_bitmask=BitMask64(UserBitmap.USER_PLAN_GUEST),
        )
        # print(doc)
        # print()
        # print(result_redacted)
        self.assertEqual(
            result_redacted[settings.IMPRESSO_SOLR_FL_CONTENT_LABEL],
            settings.IMPRESSO_CONTENT_REDACTED_LABEL,
            "Content is not available: the user has a 0 in the right position, the content item is not available",
        )
        self.assertEqual(
            result_redacted[settings.IMPRESSO_SOLR_FL_TITLE_LABEL],
            "------CE TEXTE EST PROTÉGÉ PAR LE DROIT D'AUTEUR ET NE PEUT ÊTRE UTILISÉ SANS AUTORISATION.",
            "Title is available: it is metadata",
        )


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
    "cc_b": True,
}

PROTECTED_SOLR_DOC: Dict[str, Any] = {
    "id": "abcdefgh-1882-01-21-a-i0004",
    "meta_journal_s": "abcdefgh",
    "meta_year_i": 1882,
    "meta_month_i": 1,
    "meta_yearmonth_s": "1882-01",
    "meta_day_i": 21,
    "meta_ed_s": "a",
    "meta_date_dt": "1882-01-21T00:00:00Z",
    "meta_issue_id_s": "abcdefgh-1882-01-21-a",
    "meta_source_type_s": "newspaper",
    "page_id_ss": ["abcdefgh-1882-01-21-a-p0002"],
    "page_nb_is": [2],
    "nb_pages_i": 1,
    "front_b": False,
    "reading_order_i": 4,
    "meta_country_code_s": "LU",
    "meta_province_code_s": "na",
    "meta_periodicity_s": "na",
    "meta_topics_s": "Satirical",
    "meta_polorient_s": "na",
    "meta_partnerid_s": "BNL",
    "rights_data_domain_s": "prt",
    "rights_copyright_s": "in_cpy",
    "rights_perm_use_explore_plain": "prs-rsh-edu",
    "rights_perm_use_get_tr_plain": "rsh",
    "rights_perm_use_get_img_plain": "rsh",
    "rights_bm_explore_l": 10,
    "rights_bm_get_tr_l": 1000000,
    "rights_bm_get_img_l": 1000000,
    "doc_type_s": "ci",
    "item_type_s": "ar",
    "olr_b": True,
    "lg_orig_s": "fr",
    "lg_s": "fr",
    "content_txt_fr": "------CE TEXTE EST PROTÉGÉ PAR LE DROIT D'AUTEUR ET NE PEUT ÊTRE UTILISÉ SANS AUTORISATION.",
    "content_length_i": 34,
    "snippet_plain": "-------CE TEXTE EST PROTÉGÉ PAR LE DROIT D'AUTEUR ET NE PEUT ÊTRE UTILISÉ SANS AUTORISATION.",
    "title_txt_fr": "------CE TEXTE EST PROTÉGÉ PAR LE DROIT D'AUTEUR ET NE PEUT ÊTRE UTILISÉ SANS AUTORISATION.",
    "cc_b": True,
    "ocrqa_f": 0.9,
    "_version_": 1830940593239359489,
}
