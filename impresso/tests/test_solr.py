import unittest
from impresso.utils.solr import serialize_solr_doc_content_item_to_plain_dict
from impresso.utils.solr import mapper_doc_redact_contents
from impresso.utils.bitmask import BitMask64


class SolrTestCase(unittest.TestCase):
    # def test_JsonWithBitmapDecoder(self):
    #     # Test the JsonWithBitmapDecoder with a valid input
    #     original = '{"bm_get_tr_bin": 0b1010}'
    #     result = json.loads(original, cls=JsonWithBitmapDecoder)

    #     self.assertEqual(result, {"bm_get_tr_bin": "0101"})
    def test_serialize_solr_doc_content_item_to_plain_dict(self):
        # Test the function with a valid input, a document parsed from solr
        result = serialize_solr_doc_content_item_to_plain_dict(FAKE_SOLR_DOC)

        self.assertEqual(result.get("_bm_get_tr_i"), 181)
        self.assertEqual(result.get("title"), "Subskription.")
        self.assertEqual(
            result.get("content"),
            "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
        )
        self.assertEqual(result.get("size"), 103)
        self.assertEqual(result.get("country"), "LU")
        self.assertEqual(result.get("province"), "na")
        self.assertEqual(result.get("periodicity"), "na")
        self.assertEqual(result.get("year"), 1927)
        self.assertEqual(result.get("newspaper"), "johndoe")
        self.assertEqual(result.get("issue"), "johndoe-1927-11-15-a")
        self.assertEqual(result.get("content_provider"), "BNL")
        self.assertEqual(result.get("newspaper_topics"), "Women")
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
                "bm_get_tr_i": 181,
            }
        )

        # Test the function with a valid input, a document parsed from solr
        result_redacted = mapper_doc_redact_contents(
            doc={**doc},
            # not working user bitmask key
            user_bitmask=BitMask64("0000"),
        )
        self.assertEqual(result_redacted.get("content"), "[redacted]")
        self.assertEqual(result_redacted.get("title"), doc.get("title"))

        result_ok = mapper_doc_redact_contents(
            doc={**doc},
            # working user bitmask key
            user_bitmask=BitMask64("1100"),  # 0b10110101
        )
        self.assertEqual(
            result_ok.get("content"),
            "Subskription. Gebet gerne! Wer durch eine Geldspende soziales Schaffen ermöglicht,",
            "Content is available: the user has a 1 in the right position, the content item is available",
        )


FAKE_SOLR_DOC = {
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
    "access_right_s": "OpenPublic",
    "score": 1.0,
    "exportable_plain": None,
    "topics_dpfs": [
        "tm-de-all-v2.0_tp01_de|0.02 tm-de-all-v2.0_tp03_de|0.166 tm-de-all-v2.0_tp11_de|0.026 "
    ],
    "ucoll_ss": None,
    "bm_get_tr_s": None,
    "bm_get_tr_bin": None,
    "bm_get_tr_i": 181,
}
