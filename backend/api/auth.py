"""Google OpenID sign-in. Mock mode creates a local demo identity only."""
import secrets
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.api.security import require_csrf
from backend.config.settings import settings
from backend.database.models import User
from backend.database.session import get_db
from backend.repositories.user_repository import get_or_create_google_user

router = APIRouter()
oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url=f"{settings.google_oauth_base_url}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@router.get("/auth/google/start")
async def google_start(request: Request):
    if settings.mock_integrations:
        request.session["oauth_state"] = "local-demo-state"
        return RedirectResponse(
            url=f"{settings.backend_url}/auth/google/callback?state=local-demo-state&code=local-demo"
        )
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth credentials are not configured.")
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if settings.mock_integrations:
        expected_state = request.session.pop("oauth_state", None)
        if not expected_state or request.query_params.get("state") != expected_state:
            raise HTTPException(status_code=400, detail="Invalid demo OAuth state.")
        identity = {
            "sub": "local-demo-user",
            "email": "demo@example.test",
            "name": "Demo User",
            "picture": None,
        }
    else:
        try:
            token = await oauth.google.authorize_access_token(request)
            identity = token.get("userinfo") or {}
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Google sign-in failed.") from exc
        if (
            not identity.get("sub")
            or not identity.get("email")
            or identity.get("email_verified") is not True
        ):
            raise HTTPException(status_code=400, detail="Google did not return a verified user profile.")

    user = get_or_create_google_user(
        db,
        google_sub=identity["sub"],
        email=identity["email"],
        full_name=identity.get("name", ""),
        profile_picture=identity.get("picture"),
    )
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return RedirectResponse(url=settings.frontend_url)


@router.get("/api/me")
async def current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session user no longer exists.")
    csrf_token = request.session.get("csrf_token")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = csrf_token
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "picture": user.profile_picture,
        "csrf_token": csrf_token,
    }


@router.post("/auth/logout")
async def logout(
    request: Request,
    csrf_token: str = Depends(require_csrf),
):
    request.session.clear()
    return {"status": "signed_out"}
