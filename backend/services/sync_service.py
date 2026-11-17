"""Background sync runner using a fresh DB session and the LangGraph pipeline."""
from datetime import datetime, timezone
from sqlalchemy import select
from backend.agents.graph import run_analysis_workflow
from backend.database.models import SyncRun
from backend.database.session import SessionLocal


async def execute_sync_job(user_id: str, job_id: str) -> None:
    """Run one queued job and persist terminal status without sharing request sessions."""
    db = SessionLocal()
    try:
        run = db.scalar(
            select(SyncRun).where(SyncRun.id == job_id, SyncRun.user_id == user_id)
        )
        if run is None or run.status != "queued":
            return
        run.status = "running"
        db.commit()

        result = await run_analysis_workflow(user_id, db)
        run = db.get(SyncRun, job_id)
        if run is not None:
            run.status = "completed"
            run.processed = result.get("persisted_count", 0)
            run.failed = result.get("failed_count", 0)
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(SyncRun, job_id)
        if run is not None:
            run.status = "failed"
            run.error_message = str(exc)[:1000]
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
