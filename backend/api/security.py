"""CSRF protection for cookie-authenticated state-changing routes."""
import secrets
from fastapi import Header, HTTPException, Request


def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> str:
    expected = request.session.get("csrf_token")
    if not expected or not x_csrf_token or not secrets.compare_digest(expected, x_csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")
    return expected
