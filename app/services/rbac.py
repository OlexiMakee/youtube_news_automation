"""Small request-level RBAC helpers.

This is intentionally token-backed until full user sessions exist. It prevents
client-submitted roles from becoming trusted server roles.
"""

from __future__ import annotations

import hmac
import os
from functools import wraps
from typing import Callable, Optional

from flask import jsonify, request


ADMIN_ROLES = {"admin", "master_admin"}


def configured_admin_token() -> str:
    return os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN", "").strip()


def extract_request_token(req=request) -> str:
    token = req.headers.get("X-Admin-Token", "").strip()
    if token:
        return token

    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()

    # Compatibility only. Headers are preferred because query params leak into logs.
    return (req.args.get("admin_token") or "").strip()


def has_admin_access(req=request) -> bool:
    env_token = configured_admin_token()
    if not env_token:
        # Local-first compatibility: no configured token means single-user admin mode.
        return True
    token = extract_request_token(req)
    return bool(token) and hmac.compare_digest(token, env_token)


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
    return wrapper
