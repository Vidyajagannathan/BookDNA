import re
import unittest

from worker.src.booktok import CATEGORIES, SOURCES, UPDATED, WORKS


class TestBookTokCollection(unittest.TestCase):
    def test_work_ids_are_exact_unique_open_library_ids(self):
        ids = [work_id for work_id, _category in WORKS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 20)
        self.assertTrue(all(re.fullmatch(r"OL\d+W", work_id) for work_id in ids))

    def test_every_work_uses_a_visible_category(self):
        visible = set(CATEGORIES) - {"All"}
        self.assertTrue(visible)
        self.assertTrue(all(category in visible for _work_id, category in WORKS))

    def test_collection_is_dated_and_source_backed(self):
        self.assertRegex(UPDATED, r"^\d{4}-\d{2}-\d{2}$")
        self.assertGreaterEqual(len(SOURCES), 2)
        self.assertTrue(all(source["name"] and source["url"].startswith("https://") for source in SOURCES))


if __name__ == "__main__":
    unittest.main()
