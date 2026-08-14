import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "worker" / "src"))
from dna.mappings import classify_book, map_subjects, plan_library_classifications


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

    def test_subject_matching_uses_word_boundaries(self):
        self.assertNotIn("War", {trait["name"] for trait in map_subjects(["Award-winning fiction"])})

    def test_broader_reader_taxonomy(self):
        names={trait["name"] for trait in map_subjects(["Memoirs", "Graphic novels", "Young adult fiction", "Economics", "Self help"])}
        self.assertTrue({"Memoir","Graphic Novels","Young Adult","Economics","Personal Growth"} <= names)

    def test_acotar_uses_verified_series_fallback(self):
        result=classify_book({"title":"A Court of Mist and Fury","author":"Sarah J. Maas","subjects":[]})
        self.assertEqual(result["source"],"verified_series")
        self.assertEqual(result["series_id"],"acotar")
        self.assertEqual(result["format_type"],"single")
        self.assertTrue({"Fantasy","Romance","Romantasy","Adventure"} <= {trait["name"] for trait in result["traits"]})

    def test_spectacular_is_a_single_caraval_novella(self):
        result=classify_book({"title":"Spectacular: A Caraval Holiday Novella","author":"Stephanie Garber","subjects":[]})
        self.assertEqual(result["series_id"],"caraval")
        self.assertEqual(result["matched_titles"],["spectacular"])
        self.assertEqual(result["format_type"],"single")

    def test_brothers_hawthorne_uses_inheritance_games_rule(self):
        result=classify_book({"title":"The Brothers Hawthorne","author":"Jennifer Lynn Barnes","subjects":[]})
        self.assertEqual(result["series_id"],"inheritance-games")
        self.assertTrue({"Mystery","Thriller","Romance"} <= {trait["name"] for trait in result["traits"]})

    def test_author_alone_never_assigns_a_series(self):
        result=classify_book({"title":"An Unrelated Future Novel","author":"Sarah J. Maas","subjects":[]})
        self.assertIsNone(result["series_id"])
        self.assertEqual(result["traits"],[])

    def test_unrelated_slash_title_is_not_assumed_to_be_a_collection(self):
        result=classify_book({"title":"Either / Or","author":"Elif Batuman","subjects":[]})
        self.assertEqual(result["format_type"],"single")

    def test_acotar_combined_record_is_one_collection(self):
        title="A Court of Thorns and Roses / A Court of Mist and Fury / A Court of Wings and Ruin / A Court of Frost and Starlight"
        result=classify_book({"title":title,"author":"Sarah J. Maas","subjects":[]})
        self.assertEqual(result["format_type"],"collection")

    def test_verified_series_box_set_represents_all_known_volumes(self):
        result=classify_book({"title":"A Court of Thorns and Roses Hardcover Box Set","author":"Sarah J. Maas","subjects":[]})
        self.assertEqual(result["format_type"],"collection")
        self.assertEqual(result["series_id"],"acotar")
        self.assertEqual(len(result["matched_titles"]),5)

    def test_collection_overlap_is_only_partially_counted(self):
        collection="A Court of Thorns and Roses / A Court of Mist and Fury / A Court of Wings and Ruin / A Court of Frost and Starlight"
        plans=plan_library_classifications([
            {"book_id":"mist","status":"READ","book":{"title":"A Court of Mist and Fury","author":"Sarah J. Maas","subjects":[]}},
            {"book_id":"set","status":"READ","book":{"title":collection,"author":"Sarah J. Maas","subjects":[]}},
        ])
        self.assertEqual(plans["set"]["state"],"partial_collection")
        self.assertEqual(plans["set"]["duplicate_titles"],["a court of mist and fury"])
        self.assertEqual(plans["set"]["coverage"],.75)

    def test_fully_overlapping_collection_contributes_no_evidence(self):
        collection="A Court of Thorns and Roses / A Court of Mist and Fury"
        plans=plan_library_classifications([
            {"book_id":"first","status":"READ","book":{"title":"A Court of Thorns and Roses","author":"Sarah J. Maas","subjects":[]}},
            {"book_id":"second","status":"READ","book":{"title":"A Court of Mist and Fury","author":"Sarah J. Maas","subjects":[]}},
            {"book_id":"set","status":"READ","book":{"title":collection,"author":"Sarah J. Maas","subjects":[]}},
        ])
        self.assertEqual(plans["set"]["state"],"duplicate_excluded")
        self.assertEqual(plans["set"]["coverage"],0)


if __name__ == "__main__":
    unittest.main()
