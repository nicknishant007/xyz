"""Create initial Gmail manager tables.

Revision ID: 20261117_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20261117_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("google_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("profile_picture", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "gmail_connections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("connected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("gmail_address", sa.String(length=320), nullable=True),
        sa.Column("history_id", sa.String(length=255), nullable=True),
        sa.Column("last_successful_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_gmail_connections_user_id", "gmail_connections", ["user_id"], unique=True)

    op.create_table(
        "email_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("sender_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("sender_email", sa.String(length=320), server_default="", nullable=False),
        sa.Column("subject", sa.String(length=998), server_default="", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), server_default="Other", nullable=False),
        sa.Column("category_source", sa.String(length=16), server_default="ai", nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("reply_decision", sa.String(length=16), server_default="review", nullable=False),
        sa.Column("reply_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("key_points", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("deadline", sa.String(length=255), nullable=True),
        sa.Column("suggested_reply", sa.Text(), nullable=True),
        sa.Column("draft_id", sa.String(length=255), nullable=True),
        sa.Column("draft_status", sa.String(length=16), server_default="none", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "thread_id", name="uq_user_thread"),
    )
    op.create_index("ix_email_summaries_user_id", "email_summaries", ["user_id"])
    op.create_index("ix_email_summaries_thread_id", "email_summaries", ["thread_id"])
    op.create_index("ix_email_summaries_received_at", "email_summaries", ["received_at"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="queued", nullable=False),
        sa.Column("processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sync_runs_user_id", "sync_runs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_sync_runs_user_id", table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index("ix_email_summaries_received_at", table_name="email_summaries")
    op.drop_index("ix_email_summaries_thread_id", table_name="email_summaries")
    op.drop_index("ix_email_summaries_user_id", table_name="email_summaries")
    op.drop_table("email_summaries")
    op.drop_index("ix_gmail_connections_user_id", table_name="gmail_connections")
    op.drop_table("gmail_connections")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_table("users")
