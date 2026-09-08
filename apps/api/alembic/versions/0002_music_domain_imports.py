"""Add canonical music entities and CSV import provenance tables."""

from alembic import op
import sqlalchemy as sa

revision = "0002_music_domain_imports"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

json_default = sa.text("'{}'")


def upgrade() -> None:
    uuid = sa.Uuid()
    now = sa.text("now()")
    op.create_table("artists", sa.Column("id", uuid, primary_key=True), sa.Column("canonical_name", sa.String(300), nullable=False), sa.Column("normalized_name", sa.String(300), nullable=False), sa.Column("external_ids", sa.JSON(), nullable=False, server_default=json_default), sa.Column("metadata", sa.JSON(), nullable=False, server_default=json_default))
    op.create_index("ix_artists_normalized_name", "artists", ["normalized_name"])
    op.create_table("albums", sa.Column("id", uuid, primary_key=True), sa.Column("artist_id", uuid, sa.ForeignKey("artists.id", ondelete="SET NULL")), sa.Column("canonical_title", sa.String(300), nullable=False), sa.Column("normalized_title", sa.String(300), nullable=False), sa.Column("release_date", sa.String(32)), sa.Column("external_ids", sa.JSON(), nullable=False, server_default=json_default), sa.Column("metadata", sa.JSON(), nullable=False, server_default=json_default))
    op.create_index("ix_albums_normalized_title", "albums", ["normalized_title"])
    op.create_table("tracks", sa.Column("id", uuid, primary_key=True), sa.Column("canonical_title", sa.String(300), nullable=False), sa.Column("normalized_title", sa.String(300), nullable=False), sa.Column("primary_artist_id", uuid, sa.ForeignKey("artists.id", ondelete="SET NULL")), sa.Column("album_id", uuid, sa.ForeignKey("albums.id", ondelete="SET NULL")), sa.Column("duration_ms", sa.Integer()), sa.Column("version_type", sa.String(32), nullable=False, server_default="original"), sa.Column("external_ids", sa.JSON(), nullable=False, server_default=json_default), sa.Column("metadata", sa.JSON(), nullable=False, server_default=json_default))
    op.create_index("ix_tracks_normalized_title", "tracks", ["normalized_title"])
    op.create_table("track_artists", sa.Column("track_id", uuid, sa.ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True), sa.Column("artist_id", uuid, sa.ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True), sa.Column("role", sa.String(32), primary_key=True, server_default="primary"))
    op.create_unique_constraint("uq_track_artist_role", "track_artists", ["track_id", "artist_id", "role"])
    op.create_table("track_features", sa.Column("id", uuid, primary_key=True), sa.Column("track_id", uuid, sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False), sa.Column("feature_source", sa.String(100), nullable=False), sa.Column("features", sa.JSON(), nullable=False, server_default=json_default), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_index("ix_track_features_track_id", "track_features", ["track_id"])
    op.create_table("import_batches", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("source_type", sa.String(64), nullable=False, server_default="csv"), sa.Column("source_metadata", sa.JSON(), nullable=False, server_default=json_default), sa.Column("status", sa.String(32), nullable=False, server_default="completed"), sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"), sa.Column("resolved_records", sa.Integer(), nullable=False, server_default="0"), sa.Column("ambiguous_records", sa.Integer(), nullable=False, server_default="0"), sa.Column("unresolved_records", sa.Integer(), nullable=False, server_default="0"), sa.Column("excluded_records", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now))
    op.create_index("ix_import_batches_user_id", "import_batches", ["user_id"])
    op.create_table("raw_import_records", sa.Column("id", uuid, primary_key=True), sa.Column("batch_id", uuid, sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False), sa.Column("raw_payload", sa.JSON(), nullable=False), sa.Column("source_record_id", sa.String(300)), sa.Column("observed_at", sa.DateTime(timezone=True)), sa.Column("resolution_status", sa.String(32), nullable=False, server_default="unresolved"), sa.Column("resolution_confidence", sa.Float()), sa.Column("resolution_note", sa.Text()), sa.Column("resolved_track_id", uuid, sa.ForeignKey("tracks.id", ondelete="SET NULL")), sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_raw_import_records_batch_id", "raw_import_records", ["batch_id"])
    op.create_index("ix_raw_import_records_resolution_status", "raw_import_records", ["resolution_status"])
    op.create_table("listening_events", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("track_id", uuid, sa.ForeignKey("tracks.id", ondelete="SET NULL")), sa.Column("raw_record_id", uuid, sa.ForeignKey("raw_import_records.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("played_at", sa.DateTime(timezone=True)), sa.Column("duration_played_ms", sa.Integer()), sa.Column("completion_ratio", sa.Float()), sa.Column("event_type", sa.String(32), nullable=False, server_default="play"), sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("context", sa.JSON(), nullable=False, server_default=json_default))
    op.create_index("ix_listening_events_user_id", "listening_events", ["user_id"])
    op.create_index("ix_listening_events_track_id", "listening_events", ["track_id"])
    op.create_index("ix_listening_events_played_at", "listening_events", ["played_at"])


def downgrade() -> None:
    op.drop_table("listening_events")
    op.drop_index("ix_raw_import_records_resolution_status", table_name="raw_import_records")
    op.drop_index("ix_raw_import_records_batch_id", table_name="raw_import_records")
    op.drop_table("raw_import_records")
    op.drop_index("ix_import_batches_user_id", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_index("ix_track_features_track_id", table_name="track_features")
    op.drop_table("track_features")
    op.drop_constraint("uq_track_artist_role", "track_artists", type_="unique")
    op.drop_table("track_artists")
    op.drop_index("ix_tracks_normalized_title", table_name="tracks")
    op.drop_table("tracks")
    op.drop_index("ix_albums_normalized_title", table_name="albums")
    op.drop_table("albums")
    op.drop_index("ix_artists_normalized_name", table_name="artists")
    op.drop_table("artists")
