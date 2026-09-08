"""Add user-track relationships and profile snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0003_user_intelligence"
down_revision = "0002_music_domain_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    now = sa.text("now()")
    op.create_table(
        "user_track_relationships",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", uuid, sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_played_at", sa.DateTime(timezone=True)),
        sa.Column("play_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_avg", sa.Float()),
        sa.Column("total_duration_played_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("favorite_state", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("explicit_feedback", sa.String(32)),
        sa.Column("discovery_source", sa.String(100)),
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.UniqueConstraint("user_id", "track_id", name="uq_user_track_relationship"),
    )
    op.create_index("ix_user_track_relationships_user_id", "user_track_relationships", ["user_id"])
    op.create_index("ix_user_track_relationships_track_id", "user_track_relationships", ["track_id"])
    op.create_table(
        "profile_snapshots",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_type", sa.String(32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True)),
        sa.Column("window_end", sa.DateTime(timezone=True)),
        sa.Column("window_days", sa.Integer()),
        sa.Column("features", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_index("ix_profile_snapshots_user_id", "profile_snapshots", ["user_id"])
    op.create_index("ix_profile_snapshots_profile_type", "profile_snapshots", ["profile_type"])


def downgrade() -> None:
    op.drop_index("ix_profile_snapshots_profile_type", table_name="profile_snapshots")
    op.drop_index("ix_profile_snapshots_user_id", table_name="profile_snapshots")
    op.drop_table("profile_snapshots")
    op.drop_index("ix_user_track_relationships_track_id", table_name="user_track_relationships")
    op.drop_index("ix_user_track_relationships_user_id", table_name="user_track_relationships")
    op.drop_table("user_track_relationships")

