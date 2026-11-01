"""JWT bearer verification: HS256 (shared secret) and OIDC RS256 (JWKS).

Claims mapping: sub -> actor, role -> role (default viewer),
workspace (or workspace_id) -> workspace (default "default").
Tokens are verified, never trusted blindly: signature, exp, and — when
configured — iss/aud are all checked.
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.request

from app.config import settings
from app.security import Principal

_jwks_cache: dict = {"url": None, "keys": []}


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _decode_unverified(token: str) -> tuple[dict, dict, bytes, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed JWT")
    header = json.loads(_b64url_decode(parts[0]))
    payload = json.loads(_b64url_decode(parts[1]))
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    signature = _b64url_decode(parts[2])
    return header, payload, signing_input, signature


def _check_claims(payload: dict) -> None:
    now = time.time()
    exp = payload.get("exp")
    if exp is not None and now >= float(exp):
        raise ValueError("Token expired")
    nbf = payload.get("nbf")
    if nbf is not None and now < float(nbf):
        raise ValueError("Token not yet valid")
    if settings.RW_OIDC_ISSUER and payload.get("iss") != settings.RW_OIDC_ISSUER:
        raise ValueError("Issuer mismatch")
    if settings.RW_OIDC_AUDIENCE:
        aud = payload.get("aud")
        audiences = aud if isinstance(aud, list) else [aud]
        if settings.RW_OIDC_AUDIENCE not in audiences:
            raise ValueError("Audience mismatch")


def _principal_from(payload: dict) -> Principal:
    role = payload.get("role", "viewer")
    if role not in ("admin", "editor", "viewer"):
        role = "viewer"
    return Principal(
        actor=f"jwt:{payload.get('sub', 'unknown')}",
        role=role,
        workspace=payload.get("workspace") or payload.get("workspace_id") or "default",
    )


def _verify_hs256(signing_input: bytes, signature: bytes, secret: str) -> bool:
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


def fetch_jwks(url: str) -> list[dict]:
    """Fetch (and cache per-process) an OIDC JWKS document."""
    if _jwks_cache["url"] == url and _jwks_cache["keys"]:
        return _jwks_cache["keys"]
    with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 (configured IdP URL)
        doc = json.loads(resp.read().decode())
    _jwks_cache.update({"url": url, "keys": doc.get("keys", [])})
    return _jwks_cache["keys"]


def _verify_rs256(signing_input: bytes, signature: bytes, header: dict) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    keys = fetch_jwks(settings.RW_OIDC_JWKS_URL)
    kid = header.get("kid")
    for jwk in keys:
        if kid is not None and jwk.get("kid") != kid:
            continue
        try:
            n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
            e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
            public_key = rsa.RSAPublicNumbers(e, n).public_key()
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return True
        except InvalidSignature:
            continue
        except Exception:
            continue
    return False


def verify_jwt(token: str) -> Principal | None:
    """Return the token's principal, or None if verification fails."""
    try:
        header, payload, signing_input, signature = _decode_unverified(token)
        alg = header.get("alg")
        if alg == "HS256" and settings.RW_JWT_SECRET:
            if not _verify_hs256(signing_input, signature, settings.RW_JWT_SECRET):
                return None
        elif alg == "RS256" and settings.RW_OIDC_JWKS_URL:
            if not _verify_rs256(signing_input, signature, header):
                return None
        else:
            return None
        _check_claims(payload)
        return _principal_from(payload)
    except Exception:
        return None
