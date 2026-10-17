"""Local-only authentication primitives; no seeded users or passwords."""
import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError('Passwords require at least 12 characters')
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt, expected = encoded.split('$')
        if scheme != 'scrypt' or len(password) > 1024:
            return False
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt, validate=True), n=16384, r=8, p=1)
        return hmac.compare_digest(digest, base64.b64decode(expected, validate=True))
    except (ValueError, TypeError):
        return False
