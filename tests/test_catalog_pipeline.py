import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from catalog_pipeline.models import CanonicalRecord, normalize_isbn
from catalog_pipeline.pipeline import CatalogPipeline
from catalog_pipeline.sources import crossref, datacite, doab_oai, gutenberg, openlibrary


class TestIdentifiers(__import__("unittest").TestCase):
    def test_isbn10_converts_to_valid_isbn13(self):
        self.assertEqual(normalize_isbn("0-306-40615-2"),"9780306406157")

    def test_invalid_isbn_is_rejected(self):
        self.assertIsNone(normalize_isbn("9780306406158"))

    def test_invalid_isbn_is_not_preserved(self):
        record=CanonicalRecord("example","1","A title",identifiers={"isbn":["1007363"]}).normalized()
        self.assertNotIn("isbn",record.identifiers)

    def test_ids_are_deterministic(self):
        first=CanonicalRecord("loc","1","Cien años de soledad",authors=["Gabriel García Márquez"],language="spa")
        second=CanonicalRecord("loc","2","Cien años de soledad",authors=["Gabriel García Márquez"],language="spa")
        self.assertEqual(first.work_id,second.work_id)


class TestSourceParsers(__import__("unittest").TestCase):
    def test_crossref_excludes_chapters(self):
        self.assertIsNone(crossref({"DOI":"10/x","type":"book-chapter","title":["Chapter"]}))

    def test_crossref_accepts_book(self):
        result=crossref({"DOI":"10/x","type":"book","title":["Book"],"author":[{"given":"Ada","family":"Lovelace"}],"publisher":"Press","ISBN":["9780306406157"]})
        self.assertEqual(result.quality,"A")

    def test_datacite_excludes_dataset(self):
        self.assertIsNone(datacite({"id":"10/x","attributes":{"types":{"resourceTypeGeneral":"Dataset"},"titles":[{"title":"Data"}]}}))

    def test_openlibrary_keeps_isbnless_authorless_edition(self):
        result=openlibrary({"type":{"key":"/type/edition"},"key":"/books/OL1M","title":"Anonymous text"})
        self.assertEqual(result.quality,"C")

    def test_doab_oai_maps_metadata(self):
        result=doab_oai({"source_id":"oai:1","metadata":{"title":["Open Book"],"creator":["A. Writer"],"identifier":["ISBN 9780306406157"]}})
        self.assertEqual(result.title,"Open Book")

    def test_gutenberg_has_canonical_access_link(self):
        result=gutenberg({"Text#":"42","Title":"The Answer","Authors":"A; B","Language":"en"})
        self.assertEqual(result.access_url,"https://www.gutenberg.org/ebooks/42")


class TestPipeline(__import__("unittest").TestCase):
    def test_deduplicates_isbn_and_preserves_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            pipeline=CatalogPipeline(Path(directory))
            try:
                left=CanonicalRecord("openlibrary","OL1M","A Book",authors=["An Author"],identifiers={"isbn":["9780306406157"]}).normalized()
                right=CanonicalRecord("loc","lccn1","A Book",authors=["An Author"],publisher="Press",identifiers={"isbn":["9780306406157"]}).normalized()
                pipeline.ingest("openlibrary",[left]); pipeline.ingest("loc",[right])
                report=pipeline.report()
                self.assertEqual(report["counts"]["editions"],1)
                self.assertEqual(report["counts"]["source_claims"],2)
            finally: pipeline.close()

    def test_resume_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            pipeline=CatalogPipeline(Path(directory))
            try:
                record=CanonicalRecord("gutenberg","1","A Book").normalized()
                pipeline.ingest("gutenberg",[record],cursor="one")
                pipeline.ingest("gutenberg",[record],cursor="two")
                self.assertEqual(pipeline.report()["counts"]["editions"],1)
                self.assertEqual(pipeline.checkpoint("gutenberg")["cursor"],"two")
            finally: pipeline.close()

    def test_archive_cap_stops_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); pipeline=CatalogPipeline(root/"work")
            try:
                pipeline.ingest("gutenberg",[CanonicalRecord("gutenberg","1","A Book")])
                with self.assertRaises(RuntimeError): pipeline.export_archive(root/"archive",archive_cap=1)
            finally: pipeline.close()
