"""Add local audio assets, separation jobs, and stem artifacts."""

from alembic import op
import sqlalchemy as sa


revision = "0006_audio_separation"
down_revision = "0005_timeline_memories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    now = sa.text("now()")
    op.create_table(
        "audio_assets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("source_storage_key", sa.String(500), nullable=False),
        sa.Column("normalized_storage_key", sa.String(500), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("source_size_bytes", sa.Integer(), nullable=False),
        sa.Column("source_content_type", sa.String(120)),
        sa.Column("source_codec", sa.String(64)),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("sample_rate", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Integer(), nullable=False),
        sa.Column("effective_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_index("ix_audio_assets_user_id", "audio_assets", ["user_id"])
    op.create_index("ix_audio_assets_source_sha256", "audio_assets", ["source_sha256"])
    op.create_index("ix_audio_assets_effective_deleted", "audio_assets", ["effective_deleted"])

    op.create_table(
        "separation_jobs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", uuid, sa.ForeignKey("audio_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("separator", sa.String(100), nullable=False),
        sa.Column("separator_version", sa.String(64), nullable=False),
        sa.Column("model_checkpoint", sa.String(200), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("error_detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "fingerprint", name="uq_separation_job_user_fingerprint"),
    )
    op.create_index("ix_separation_jobs_user_id", "separation_jobs", ["user_id"])
    op.create_index("ix_separation_jobs_asset_id", "separation_jobs", ["asset_id"])
    op.create_index("ix_separation_jobs_status", "separation_jobs", ["status"])
    op.create_index("ix_separation_jobs_fingerprint", "separation_jobs", ["fingerprint"])

    op.create_table(
        "stem_artifacts",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("job_id", uuid, sa.ForeignKey("separation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stem_name", sa.String(32), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("sample_rate", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.UniqueConstraint("job_id", "stem_name", name="uq_stem_artifact_job_stem"),
    )
    op.create_index("ix_stem_artifacts_job_id", "stem_artifacts", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_stem_artifacts_job_id", table_name="stem_artifacts")
    op.drop_table("stem_artifacts")
    op.drop_index("ix_separation_jobs_fingerprint", table_name="separation_jobs")
    op.drop_index("ix_separation_jobs_status", table_name="separation_jobs")
    op.drop_index("ix_separation_jobs_asset_id", table_name="separation_jobs")
    op.drop_index("ix_separation_jobs_user_id", table_name="separation_jobs")
    op.drop_table("separation_jobs")
    op.drop_index("ix_audio_assets_effective_deleted", table_name="audio_assets")
    op.drop_index("ix_audio_assets_source_sha256", table_name="audio_assets")
    op.drop_index("ix_audio_assets_user_id", table_name="audio_assets")
    op.drop_table("audio_assets")
