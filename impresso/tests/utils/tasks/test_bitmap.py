import unittest
from ...test_solr import FAKE_SOLR_DOC
from impresso.solr import serialize_solr_doc_content_item_to_plain_dict
from impresso.utils.tasks import mapper_doc_redact_contents


class BitmapTestCase(unittest.TestCase):
    def test_mapper_doc_redact_contents(self):
        doc = serialize_solr_doc_content_item_to_plain_dict(FAKE_SOLR_DOC)
        # Test the function with a valid input, a document parsed from solr
        result = mapper_doc_redact_contents(
            doc=doc,
            user_bitmap_key="user_bitmap_key",
        )
        self.assertEqual(result.get("content"), "[redacted]")
        self.assertEqual(result.get("content"), "[redacted]")
        self.assertEqual(result.get("title"), doc.get("title"))

        # test with a working user biutmap key
        print(doc)
