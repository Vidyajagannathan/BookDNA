import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"worker"/"src"))
from security.tokens import create_token, hash_password, verify_password, verify_token

class TestSecurity(__import__("unittest").TestCase):
    def test_password_round_trip(self):
        encoded=hash_password("Correct horse battery staple")
        self.assertTrue(verify_password("Correct horse battery staple",encoded))
        self.assertFalse(verify_password("wrong",encoded))

    def test_access_token_round_trip(self):
        token=create_token("usr_test","session_test","secret",60)
        payload=verify_token(token,"secret")
        self.assertEqual(payload["sub"],"usr_test")
        self.assertIsNone(verify_token(token,"different"))
