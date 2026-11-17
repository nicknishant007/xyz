"""Persistence operations for authenticated user identities."""
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.database.models import User


def get_or_create_google_user(
    db: Session,
    *,
    google_sub: str,
    email: str,
    full_name: str = "",
    profile_picture: str | None = None,
) -> User:
    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and user.google_sub != google_sub:
            raise ValueError("Google identity does not match the existing account.")
        if user is None:
            user = User(id=str(uuid4()), google_sub=google_sub, email=email)
            db.add(user)
    user.google_sub = google_sub
    user.email = email
    user.full_name = full_name
    user.profile_picture = profile_picture
    db.commit()
    db.refresh(user)
    return user
