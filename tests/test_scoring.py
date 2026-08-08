import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"worker"/"src"))
from dna.scoring import Signal, contribution, display_score, similarity

class TestScoring(__import__("unittest").TestCase):
    def test_want_to_read_is_not_identity(self): self.assertEqual(contribution(Signal("WANT_TO_READ",5,True),{"fantasy":1}),{})
    def test_favourite_five_star_has_locked_multiplier(self): self.assertEqual(contribution(Signal("READ",5,True),{"fantasy":1})["fantasy"],1.6875)
    def test_dnf_not_positive(self): self.assertEqual(contribution(Signal("DNF",5,True),{"dense":1}),{})
    def test_confidence_shrinks_small_evidence(self): self.assertLess(display_score(.9,.9),70)
    def test_cosine_similarity(self):
        self.assertEqual(similarity({"a":1},{"a":1}),100)
        self.assertEqual(similarity({"a":1},{"b":1}),0)
