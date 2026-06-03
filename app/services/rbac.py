"""Small request-level RBAC helpers.

Admin roles are derived from a configured server token or from server-side
sessions minted by that token. Client-submitted roles are never trusted.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from functools import wraps
from typing import Callable, Dict, Optional

from flask import jsonify, request


ADMIN_ROLES = {"admin", "master_admin"}
# TODO Phase 1: Add Reader, Analyst roles gated by entitlement flags (ready_workspace, dense_workspace, linked_intelligence).
# Reader: read-only briefs, source cards. Analyst: edit filters, mark evidence, save layouts. Admin: all + governance.
ADMIN_SESSION_COOKIE = "news_research_admin_session"
ADMIN_SESSION_TTL_SECONDS = 12 * 60 * 60
_session_lock = threading.RLock()
_admin_sessions: Dict[str, Dict[str, object]] = {}


def configured_admin_token() -> str:
    return os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN", "").strip()


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _prune_expired_sessions(now: Optional[int] = None) -> None:
    cutoff = int(now or time.time())
    expired = [
        session_id for session_id, session in _admin_sessions.items()
        if int(session.get("expires_at", 0)) <= cutoff
    ]
    for session_id in expired:
        _admin_sessions.pop(session_id, None)


def extract_request_token(req=request) -> str:
    token = req.headers.get("X-Admin-Token", "").strip()
    if token:
        return token

    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()

    # Compatibility only. Headers are preferred because query params leak into logs.
    return (req.args.get("admin_token") or "").strip()


def has_valid_admin_session(req=request) -> bool:
    env_token = configured_admin_token()
    if not env_token:
        return False

    session_id = (req.cookies.get(ADMIN_SESSION_COOKIE) or "").strip()
    if not session_id:
        return False

    now = int(time.time())
    with _session_lock:
        _prune_expired_sessions(now)
        session = _admin_sessions.get(session_id)
        if not session:
            return False
        if session.get("token_fingerprint") != _token_fingerprint(env_token):
            _admin_sessions.pop(session_id, None)
            return False
        if session.get("role") not in ADMIN_ROLES:
            return False
        session["last_seen_at"] = now
        return True


def create_admin_session(req=request) -> Optional[Dict[str, object]]:
    env_token = configured_admin_token()
    if env_token:
        request_token = extract_request_token(req)
        if not request_token or not hmac.compare_digest(request_token, env_token):
            return None

    now = int(time.time())
    session_id = secrets.token_urlsafe(32)
    session = {
        "id": session_id,
        "role": "admin",
        "created_at": now,
        "last_seen_at": now,
        "expires_at": now + ADMIN_SESSION_TTL_SECONDS,
        "token_fingerprint": _token_fingerprint(env_token),
    }
    with _session_lock:
        _prune_expired_sessions(now)
        _admin_sessions[session_id] = session
    return session


def destroy_admin_session(req=request) -> bool:
    session_id = (req.cookies.get(ADMIN_SESSION_COOKIE) or "").strip()
    if not session_id:
        return False
    with _session_lock:
        return _admin_sessions.pop(session_id, None) is not None


def has_admin_access(req=request) -> bool:
    env_token = configured_admin_token()
    if not env_token:
        # Local-first compatibility: no configured token means single-user admin mode.
        return True
    token = extract_request_token(req)
    if bool(token) and hmac.compare_digest(token, env_token):
        return True
    return has_valid_admin_session(req)


def current_request_role(req=request) -> str:
    return "admin" if has_admin_access(req) else "user"


def assistant_role_for_request(requested_role: Optional[str], req=request) -> str:
    requested = (requested_role or "user").strip().lower()
    if requested in ADMIN_ROLES and has_admin_access(req):
        return "admin"
    return "user"


def require_admin(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not has_admin_access(request):
            return jsonify({"error": "Admin access required."}), 403
        return fn(*args, **kwargs)
    wrapper._requires_admin = True
    return wrapper
