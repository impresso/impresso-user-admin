import unittest
from impresso.utils.tasks import mapper_doc_redact_contents


class InitFunctionsTestCase(unittest.TestCase):
    def test_mapper_doc_redact_contents(self):
        # Test the function with a valid input, a document parsed from solr
        result = mapper_doc_redact_contents(
            doc={
                "availability": "free",
                "year": 2020,
            },
            user_bitmap_key="user_bitmap_key",
        )
        self.assertEqual(result.get("content"), "[redacted]")
