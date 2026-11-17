"""Shared authenticated-user dependency for API routes."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.database.models import User
from backend.database.session import get_db


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session user no longer exists.")
    return user
