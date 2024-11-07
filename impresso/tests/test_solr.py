import json

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
    "access_right_s": None,
    "score": 1.0,
    "exportable_plain": None,
    "topics_dpfs": [
        "tm-de-all-v2.0_tp01_de|0.02 tm-de-all-v2.0_tp03_de|0.166 tm-de-all-v2.0_tp11_de|0.026 tm-de-all-v2.0_tp26_de|0.02 tm-de-all-v2.0_tp34_de|0.096 tm-de-all-v2.0_tp36_de|0.026 tm-de-all-v2.0_tp37_de|0.02 tm-de-all-v2.0_tp46_de|0.026 tm-de-all-v2.0_tp51_de|0.032 tm-de-all-v2.0_tp69_de|0.061 tm-de-all-v2.0_tp81_de|0.026 tm-de-all-v2.0_tp88_de|0.02 tm-de-all-v2.0_tp92_de|0.049 tm-de-all-v2.0_tp94_de|0.044 "
    ],
    "ucoll_ss": None,
    "bm_get_tr_s": None,
    "bm_get_tr_bin": "01",
}

import unittest
from impresso.solr import solr_doc_to_content_item, JsonWithBitmapDecoder


class SolrTestCase(unittest.TestCase):
    def test_JsonWithBitmapDecoder(self):
        # Test the JsonWithBitmapDecoder with a valid input
        original = '{"bm_get_tr_bin": 0b1010}'
        result = json.loads(original, cls=JsonWithBitmapDecoder)

        self.assertEqual(result, {"bm_get_tr_bin": "0101"})

    def test_solr_doc_to_content_item(self):
        # Test the function with a valid input, a document parsed from solr
        result = solr_doc_to_content_item(FAKE_SOLR_DOC)
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
