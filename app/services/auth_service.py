import base64
import hashlib
import hmac
import json
import secrets
import time

PBKDF2_ITERATIONS = 260_000
SESSION_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected_hex)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_session_token(secret: str, username: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    payload = json.dumps({"sub": username, "exp": int(time.time()) + ttl_seconds}).encode("utf-8")
    payload_b64 = _b64encode(payload)
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64encode(signature)}"


def verify_session_token(token: str, secret: str) -> bool:
    try:
        payload_b64, signature_b64 = token.split(".", 1)
    except ValueError:
        return False
    expected_signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(_b64decode(signature_b64), expected_signature):
            return False
        payload = json.loads(_b64decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return False
    return isinstance(payload.get("exp"), int) and payload["exp"] > time.time()
