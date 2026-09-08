"""Add lightweight artist concert discovery data."""

from alembic import op
import sqlalchemy as sa


revision = "0007_concert_discovery"
down_revision = "0006_audio_separation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = sa.Uuid()
    now = sa.text("now()")
    op.create_table(
        "artist_provider_identities",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("artist_id", uuid, sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_artist_id", sa.String(200)),
        sa.Column("normalized_name", sa.String(300), nullable=False),
        sa.Column("last_resolved_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.UniqueConstraint("artist_id", "provider", name="uq_artist_provider_identity"),
    )
    op.create_index("ix_artist_provider_identities_artist_id", "artist_provider_identities", ["artist_id"])
    op.create_table(
        "concert_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("artist_id", uuid, sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_event_id", sa.String(200), nullable=False),
        sa.Column("event_name", sa.String(300)),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time()),
        sa.Column("timezone_name", sa.String(80)),
        sa.Column("venue_name", sa.String(300)),
        sa.Column("city", sa.String(160)),
        sa.Column("region", sa.String(160)),
        sa.Column("country", sa.String(120)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("external_url", sa.String(1000)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("status", sa.String(32), nullable=False, server_default="upcoming"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("artist_id", "provider", "provider_event_id", name="uq_concert_artist_provider_event"),
    )
    op.create_index("ix_concert_events_artist_id", "concert_events", ["artist_id"])
    op.create_index("ix_concert_events_start_date", "concert_events", ["start_date"])
    op.create_index("ix_concert_events_fetched_at", "concert_events", ["fetched_at"])


def downgrade() -> None:
    op.drop_index("ix_concert_events_fetched_at", table_name="concert_events")
    op.drop_index("ix_concert_events_start_date", table_name="concert_events")
    op.drop_index("ix_concert_events_artist_id", table_name="concert_events")
    op.drop_table("concert_events")
    op.drop_index("ix_artist_provider_identities_artist_id", table_name="artist_provider_identities")
    op.drop_table("artist_provider_identities")
