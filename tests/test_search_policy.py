import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "worker" / "src"))

from search_policy import (
    HYBRID_REMOTE_BUDGET_SECONDS,
    catalog_year,
    local_search_text,
    merge_books,
    remote_wait_seconds,
)


class TestSearchPolicy(__import__("unittest").TestCase):
    def test_hybrid_limits_remote_wait_when_local_results_exist(self):
        self.assertEqual(remote_wait_seconds("hybrid", 1), HYBRID_REMOTE_BUDGET_SECONDS)
        self.assertEqual(remote_wait_seconds("local-first", 12), HYBRID_REMOTE_BUDGET_SECONDS)

    def test_remote_remains_authoritative_without_local_results(self):
        self.assertIsNone(remote_wait_seconds("hybrid", 0))
        self.assertIsNone(remote_wait_seconds("shadow", 10))
        self.assertIsNone(remote_wait_seconds("fallback", 0))

    def test_local_search_understands_supported_field_prefixes(self):
        self.assertEqual(local_search_text("subject:fantasy"), "fantasy")
        self.assertEqual(local_search_text("subject_key:romance"), "romance")
        self.assertEqual(local_search_text("author:J. R. R. Tolkien"), "J. R. R. Tolkien")
        self.assertEqual(local_search_text("The Hobbit"), "The Hobbit")

    def test_catalog_year_supports_local_and_api_rows(self):
        self.assertEqual(catalog_year({"published": "First published in 1954"}), 1954)
        self.assertEqual(catalog_year({"first_publish_year": 1979}), 1979)
        self.assertEqual(catalog_year({"year": "2005"}), 2005)
        self.assertEqual(catalog_year({"published": "unknown"}), 0)

    def test_merge_prefers_local_and_deduplicates_remote(self):
        local = [{"id": "local", "title": "Local"}, {"id": "shared", "title": "Local copy"}]
        remote = [{"id": "shared", "title": "Remote copy"}, {"id": "remote", "title": "Remote"}]
        self.assertEqual(
            [book["id"] for book in merge_books(local, remote, 3)],
            ["local", "shared", "remote"],
        )

    def test_merge_respects_page_limit(self):
        self.assertEqual(
            [book["id"] for book in merge_books([{"id": "one"}], [{"id": "two"}], 1)],
            ["one"],
        )

    def test_merge_deduplicates_cross_source_title_and_author(self):
        local = [{"id": "catalog-1", "title": "The Hobbit", "author": "J. R. R. Tolkien"}]
        remote = [{"id": "OL1W", "title": "The Hobbit", "author": "J. R. R. Tolkien"}]
        self.assertEqual(merge_books(local, remote, 4), local)

    def test_merge_excludes_books_from_previous_pages(self):
        previous = [{"id": "catalog-1", "title": "The Hobbit", "author": "J. R. R. Tolkien"}]
        remote = [
            {"id": "OL1W", "title": "The Hobbit", "author": "J. R. R. Tolkien"},
            {"id": "OL2W", "title": "The Silmarillion", "author": "J. R. R. Tolkien"},
        ]
        self.assertEqual(
            [book["id"] for book in merge_books([], remote, 4, excluded=previous)],
            ["OL2W"],
        )
