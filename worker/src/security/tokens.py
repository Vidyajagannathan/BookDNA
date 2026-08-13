import base64
import hashlib
import hmac
import json
import secrets
import time

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def hash_password(password: str, salt: str | None = None) -> str:
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, 120_000)
    return f"pbkdf2_sha256$120000${salt_bytes.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def create_token(user_id: str, session_id: str, secret: str, lifetime: int = 900, remember: bool = False) -> str:
    now = int(time.time()); header = _b64(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(",", ":")).encode()); payload = _b64(json.dumps({"sub":user_id,"sid":session_id,"iat":now,"exp":now+lifetime,"rem":remember}, separators=(",", ":")).encode()); signature = _b64(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()); return f"{header}.{payload}.{signature}"

def verify_token(token: str, secret: str) -> dict | None:
    try:
        header, payload, signature = token.split("."); expected = _b64(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return data if data.get("exp", 0) > time.time() else None
    except Exception:
        return None
