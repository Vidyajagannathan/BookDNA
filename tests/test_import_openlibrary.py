import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from import_openlibrary import edition_sql, key_id, work_sql


class TestOpenLibraryImport(__import__("unittest").TestCase):
    def test_key_id_handles_open_library_paths(self):
        self.assertEqual(key_id("/works/OL123W"), "OL123W")

    def test_work_is_upserted_and_indexed(self):
        statements = work_sql({"key":"/works/OL1W","title":"A Book","first_publish_date":"1984","subjects":["Science Fiction"],"authors":[{"author":{"key":"/authors/OL2A"}}],"covers":[123],"last_modified":{"value":"2026-01-01T00:00:00"}})
        self.assertEqual(len(statements), 3)
        self.assertIn("OL1W", statements[0])
        self.assertIn("catalog_works_fts", statements[2])

    def test_edition_normalizes_isbn(self):
        statements = edition_sql({"key":"/books/OL1M","title":"A Book","works":[{"key":"/works/OL1W"}],"isbn_13":["978-1-234-56789-7"]})
        self.assertTrue(any("9781234567897" in statement for statement in statements))

    def test_incomplete_records_are_skipped(self):
        self.assertEqual(work_sql({"key":"/works/OL1W"}), [])
        self.assertEqual(edition_sql({"key":"/books/OL1M","title":"No work"}), [])
