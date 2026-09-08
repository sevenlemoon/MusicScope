"""Add explicit user library membership."""

from alembic import op
import sqlalchemy as sa


revision = "0010_library_membership"
down_revision = "0009_concert_doors_time"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_library_tracks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "track_id", "source_type", "source_name", name="uq_user_library_track_source"),
    )
    op.create_index("ix_user_library_tracks_user_id", "user_library_tracks", ["user_id"])
    op.create_index("ix_user_library_tracks_track_id", "user_library_tracks", ["track_id"])
    op.create_index("ix_user_library_tracks_active", "user_library_tracks", ["active"])
    op.add_column("user_track_relationships", sa.Column("in_library", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user_track_relationships", sa.Column("first_library_imported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_track_relationships", sa.Column("library_source_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("user_track_relationships", "library_source_count")
    op.drop_column("user_track_relationships", "first_library_imported_at")
    op.drop_column("user_track_relationships", "in_library")
    op.drop_index("ix_user_library_tracks_active", table_name="user_library_tracks")
    op.drop_index("ix_user_library_tracks_track_id", table_name="user_library_tracks")
    op.drop_index("ix_user_library_tracks_user_id", table_name="user_library_tracks")
    op.drop_table("user_library_tracks")
