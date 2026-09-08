"""Add evidence-first timeline periods and user-authored memories."""

from alembic import op
import sqlalchemy as sa

revision = "0005_timeline_memories"
down_revision = "0004_recommendations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    now = sa.text("now()")
    op.create_table("timeline_periods", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("start_at", sa.DateTime(timezone=True), nullable=False), sa.Column("end_at", sa.DateTime(timezone=True), nullable=False), sa.Column("label", sa.String(120), nullable=False), sa.Column("change_score", sa.Float(), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")), sa.Column("metrics", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=now), sa.UniqueConstraint("user_id", "start_at", "end_at", name="uq_timeline_period_window"))
    op.create_index("ix_timeline_periods_user_id", "timeline_periods", ["user_id"])
    op.create_table("memories", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("target_type", sa.String(32), nullable=False), sa.Column("target_id", uuid), sa.Column("text", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_index("ix_memories_user_id", "memories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_memories_user_id", table_name="memories")
    op.drop_table("memories")
    op.drop_index("ix_timeline_periods_user_id", table_name="timeline_periods")
    op.drop_table("timeline_periods")

