"""Add recommendation runs, recommendations, and feedback events."""

from alembic import op
import sqlalchemy as sa

revision = "0004_recommendations"
down_revision = "0003_user_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    now = sa.text("now()")
    empty = sa.text("'{}'")
    op.create_table("recommendation_runs", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("exploration_level", sa.Float(), nullable=False), sa.Column("context", sa.JSON(), nullable=False, server_default=empty), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_index("ix_recommendation_runs_user_id", "recommendation_runs", ["user_id"])
    op.create_table("recommendations", sa.Column("id", uuid, primary_key=True), sa.Column("run_id", uuid, sa.ForeignKey("recommendation_runs.id", ondelete="CASCADE"), nullable=False), sa.Column("track_id", uuid, sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False), sa.Column("score", sa.Float(), nullable=False), sa.Column("role", sa.String(40), nullable=False), sa.Column("rank", sa.Integer(), nullable=False), sa.Column("explanation_evidence", sa.JSON(), nullable=False, server_default=empty), sa.Column("score_breakdown", sa.JSON(), nullable=False, server_default=empty), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_index("ix_recommendations_run_id", "recommendations", ["run_id"])
    op.create_index("ix_recommendations_track_id", "recommendations", ["track_id"])
    op.create_table("feedback_events", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("track_id", uuid, sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False), sa.Column("recommendation_id", uuid, sa.ForeignKey("recommendations.id", ondelete="SET NULL")), sa.Column("event_type", sa.String(32), nullable=False), sa.Column("reason", sa.String(64)), sa.Column("context", sa.JSON(), nullable=False, server_default=empty), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_index("ix_feedback_events_user_id", "feedback_events", ["user_id"])
    op.create_index("ix_feedback_events_track_id", "feedback_events", ["track_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_events_track_id", table_name="feedback_events")
    op.drop_index("ix_feedback_events_user_id", table_name="feedback_events")
    op.drop_table("feedback_events")
    op.drop_index("ix_recommendations_track_id", table_name="recommendations")
    op.drop_index("ix_recommendations_run_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_recommendation_runs_user_id", table_name="recommendation_runs")
    op.drop_table("recommendation_runs")

