"""HMAC provenance envelopes for v2.1 trust boundaries.

Secrets are injected by the deployment or direct caller. This module never
reads environment variables and never contains a production fallback secret.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Dict, Iterable
import hmac
import json


PROVENANCE_VERSION = "trust-envelope/1.0"
ALGORITHM = "HMAC-SHA256"
MIN_SECRET_BYTES = 32


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_digest(data: Any) -> str:
    return "sha256:" + sha256(canonical_json(data).encode("utf-8")).hexdigest()


def validate_secret(secret: str | bytes, name: str = "provenance secret") -> bytes:
    if isinstance(secret, str):
        raw = secret.encode("utf-8")
    elif isinstance(secret, bytes):
        raw = secret
    else:
        raise ValueError(f"{name} must be a string or bytes")
    if len(raw) < MIN_SECRET_BYTES:
        raise ValueError(f"{name} must contain at least {MIN_SECRET_BYTES} bytes")
    return raw


def _unsigned(payload: Dict[str, Any], ignored_fields: Iterable[str]) -> Dict[str, Any]:
    ignored = {"provenance", *ignored_fields}
    return {key: deepcopy(value) for key, value in payload.items() if key not in ignored}


def _signature_input(payload: Dict[str, Any], envelope: Dict[str, Any], ignored_fields: Iterable[str]) -> bytes:
    return canonical_json({
        "envelope": {key: value for key, value in envelope.items() if key != "signature"},
        "payload": _unsigned(payload, ignored_fields),
    }).encode("utf-8")


def sign_payload(
    payload: Dict[str, Any],
    secret: str | bytes,
    *,
    issuer: str,
    purpose: str,
    ignored_fields: Iterable[str] = (),
) -> Dict[str, Any]:
    key = validate_secret(secret)
    envelope = {
        "version": PROVENANCE_VERSION,
        "algorithm": ALGORITHM,
        "issuer": issuer,
        "purpose": purpose,
    }
    signature = hmac.new(key, _signature_input(payload, envelope, ignored_fields), sha256).hexdigest()
    result = _unsigned(payload, ())
    result["provenance"] = {**envelope, "signature": "hmac-sha256:" + signature}
    return result


def verify_payload(
    payload: Dict[str, Any],
    secret: str | bytes,
    *,
    issuer: str,
    purpose: str,
    ignored_fields: Iterable[str] = (),
) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("provenance"), dict):
        return False
    envelope = payload["provenance"]
    expected_metadata = {
        "version": PROVENANCE_VERSION,
        "algorithm": ALGORITHM,
        "issuer": issuer,
        "purpose": purpose,
    }
    if any(envelope.get(key) != value for key, value in expected_metadata.items()):
        return False
    supplied = envelope.get("signature")
    if not isinstance(supplied, str) or not supplied.startswith("hmac-sha256:"):
        return False
    try:
        key = validate_secret(secret)
    except ValueError:
        return False
    expected = hmac.new(key, _signature_input(payload, envelope, ignored_fields), sha256).hexdigest()
    return hmac.compare_digest(supplied.removeprefix("hmac-sha256:"), expected)


def sign_b_record(record: Dict[str, Any], secret: str | bytes) -> Dict[str, Any]:
    """Sign a raw B-side logger/runner record.

    ``verification_status`` is deliberately excluded: A derives that status
    from the signature and never trusts the caller-provided string.
    """
    return sign_payload(
        record,
        secret,
        issuer="skillmirror-b",
        purpose="b-runtime-record",
        ignored_fields={"verification_status"},
    )


def verify_b_record(record: Dict[str, Any], secret: str | bytes) -> bool:
    return verify_payload(
        record,
        secret,
        issuer="skillmirror-b",
        purpose="b-runtime-record",
        ignored_fields={"verification_status"},
    )


def sign_verification_record(record: Dict[str, Any], secret: str | bytes) -> Dict[str, Any]:
    return sign_payload(
        record,
        secret,
        issuer="skillmirror-a-evaluator",
        purpose="normalized-verification-record",
    )


def verify_verification_record(record: Dict[str, Any], secret: str | bytes) -> bool:
    return verify_payload(
        record,
        secret,
        issuer="skillmirror-a-evaluator",
        purpose="normalized-verification-record",
    )


def sign_evidence(evidence: Dict[str, Any], secret: str | bytes) -> Dict[str, Any]:
    return sign_payload(
        evidence,
        secret,
        issuer="skillmirror-a-evidence-engine",
        purpose="trusted-evidence",
    )


def verify_evidence(evidence: Dict[str, Any], secret: str | bytes) -> bool:
    return verify_payload(
        evidence,
        secret,
        issuer="skillmirror-a-evidence-engine",
        purpose="trusted-evidence",
    )


def sign_challenge(challenge: Dict[str, Any], secret: str | bytes) -> Dict[str, Any]:
    return sign_payload(
        challenge,
        secret,
        issuer="skillmirror-a-challenge-generator",
        purpose="internal-challenge",
    )


def verify_challenge(challenge: Dict[str, Any], secret: str | bytes) -> bool:
    return verify_payload(
        challenge,
        secret,
        issuer="skillmirror-a-challenge-generator",
        purpose="internal-challenge",
    )
