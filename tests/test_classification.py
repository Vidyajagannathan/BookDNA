import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "worker" / "src"))
from dna.mappings import classify_book, map_subjects


class TestClassification(unittest.TestCase):
    def names(self, book):
        return {trait["name"] for trait in classify_book(book)["traits"]}

    def test_requested_subject_mappings(self):
        names = {trait["name"] for trait in map_subjects([
            "Religion", "Spirituality", "Hindu philosophy", "Sacred books", "Education",
            "Science", "Hindi literature", "Hindi language", "School textbook",
        ])}
        self.assertTrue({"Religion", "Spirituality", "Hindu Philosophy", "Sacred Texts", "Education", "Science", "Hindi Literature", "Language Learning", "School Textbook"} <= names)

    def test_bhagavad_gita_title_fallback(self):
        result = classify_book({"title": "Bhagavad Gita", "author": "Vyasa", "subjects": []})
        self.assertEqual(result["source"], "title_author_fallback")
        self.assertEqual(result["reading_type"], "recreational")
        self.assertTrue({"Hindu Philosophy", "Sacred Texts", "Spirituality"} <= {trait["name"] for trait in result["traits"]})

    def test_ncert_science_is_academic(self):
        result = classify_book({"title": "Science Textbook for Class X", "author": "NCERT", "subjects": []})
        self.assertEqual(result["reading_type"], "academic")
        self.assertTrue({"Science", "Education", "School Textbook"} <= {trait["name"] for trait in result["traits"]})

    def test_vasant_is_academic_hindi_literature(self):
        result = classify_book({"title": "Vasant Part 2 NCERT Hindi Textbook for Class 7", "author": "NCERT", "subjects": []})
        self.assertEqual(result["reading_type"], "academic")
        self.assertTrue({"Hindi Literature", "Language Learning", "Education", "School Textbook"} <= {trait["name"] for trait in result["traits"]})

    def test_unknown_missing_metadata_needs_classification(self):
        result = classify_book({"title": "An Unmapped Book", "author": "Someone", "subjects": []})
        self.assertEqual(result["source"], "none")
        self.assertEqual(result["traits"], [])

    def test_science_fiction_is_not_mistaken_for_academic_science(self):
        names = {trait["name"] for trait in map_subjects(["Science fiction"])}
        self.assertIn("Science Fiction", names)
        self.assertNotIn("Science", names)


if __name__ == "__main__":
    unittest.main()
