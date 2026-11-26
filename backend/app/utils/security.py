"""Cryptographic helpers for one-time, parameter-bound approval tokens."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings


def hash_parameters(parameters: dict[str, Any]) -> str:
    """Compute a canonical SHA-256 hash of action parameters."""
    canonical = json.dumps(parameters or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_token(token: str) -> str:
    """Hash a raw approval token for safe database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_approval_token(
    action_record_id: str,
    parameters: dict[str, Any],
    ttl_seconds: int | None = None,
) -> tuple[str, str, str, datetime]:
    """Generate a one-time HMAC-signed approval token bound to action ID and parameters.

    Returns:
        (raw_token, token_hash, parameters_hash, expires_at)
    """
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.approval_token_ttl_seconds
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    params_hash = hash_parameters(parameters)
    nonce = secrets.token_urlsafe(16)
    exp_ts = int(expires_at.timestamp())

    payload = f"{action_record_id}:{params_hash}:{exp_ts}:{nonce}"
    sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    raw_token = f"{payload}:{sig}"
    return raw_token, hash_token(raw_token), params_hash, expires_at


def verify_approval_token(
    raw_token: str,
    expected_action_record_id: str,
    expected_parameters: dict[str, Any],
) -> tuple[bool, str]:
    """Verify HMAC signature, action ID binding, parameter hash binding, and expiry."""
    settings = get_settings()
    parts = raw_token.rsplit(":", 4)
    if len(parts) != 5:
        return False, "Malformed approval token."

    token_action_id, token_params_hash, exp_str, nonce, provided_sig = parts
    if token_action_id != expected_action_record_id:
        return False, "Approval token does not match this action."

    expected_params_hash = hash_parameters(expected_parameters)
    if not hmac.compare_digest(token_params_hash, expected_params_hash):
        return False, "Action parameters were modified after approval."

    try:
        exp_ts = int(exp_str)
    except ValueError:
        return False, "Invalid expiration in approval token."

    if datetime.now(timezone.utc).timestamp() > exp_ts:
        return False, "Approval token has expired."

    payload = f"{token_action_id}:{token_params_hash}:{exp_str}:{nonce}"
    expected_sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        return False, "Invalid approval token signature."

    return True, "Token valid."
