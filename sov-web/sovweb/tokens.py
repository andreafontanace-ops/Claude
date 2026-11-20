"""Link firmati e a scadenza per verifica email e recupero password."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

RESET_MAX_AGE = 3600  # 1 ora
VERIFY_MAX_AGE = 7 * 24 * 3600  # 7 giorni


def _serializer(secret: str, purpose: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=f"sovweb-{purpose}")


def password_fingerprint(password_hash: str) -> str:
    """Cambia quando cambia la password: rende i link di recupero monouso e chiude le altre sessioni."""
    return password_hash[-16:]


def make_reset_token(secret: str, user_id: int, password_hash: str) -> str:
    return _serializer(secret, "reset").dumps({"u": user_id, "p": password_fingerprint(password_hash)})


def read_reset_token(secret: str, token: str) -> dict | None:
    try:
        return _serializer(secret, "reset").loads(token, max_age=RESET_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def make_verify_token(secret: str, user_id: int, email: str) -> str:
    return _serializer(secret, "verify").dumps({"u": user_id, "e": email})


def read_verify_token(secret: str, token: str) -> dict | None:
    try:
        return _serializer(secret, "verify").loads(token, max_age=VERIFY_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
