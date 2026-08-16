from copy import deepcopy
from hashlib import sha256
from typing import Any
import hmac
import json


PROVENANCE_VERSION = "trust-envelope/1.0"
ALGORITHM = "HMAC-SHA256"


def canonical_json(data: Any) -> str:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def content_digest(data: Any) -> str:
    raw = canonical_json(data).encode("utf-8")
    return "sha256:" + sha256(raw).hexdigest()


def sign_b_record(
    record: dict[str, Any],
    secret: str,
) -> dict[str, Any]:
    secret_bytes = secret.encode("utf-8")

    if len(secret_bytes) < 32:
        raise ValueError(
            "SKILLMIRROR_B_PROVENANCE_SECRET must contain at least 32 bytes"
        )

    envelope = {
        "version": PROVENANCE_VERSION,
        "algorithm": ALGORITHM,
        "issuer": "skillmirror-b",
        "purpose": "b-runtime-record",
    }

    # provenance 和 verification_status 不参与签名。
    payload = {
        key: deepcopy(value)
        for key, value in record.items()
        if key not in {"provenance", "verification_status"}
    }

    signature_input = canonical_json({
        "envelope": envelope,
        "payload": payload,
    }).encode("utf-8")

    signature = hmac.new(
        secret_bytes,
        signature_input,
        sha256,
    ).hexdigest()

    result = {
        key: deepcopy(value)
        for key, value in record.items()
        if key != "provenance"
    }

    result["provenance"] = {
        **envelope,
        "signature": f"hmac-sha256:{signature}",
    }

    return result