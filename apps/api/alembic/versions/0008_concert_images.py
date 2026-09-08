"""Store provider-supplied concert imagery when available."""

from alembic import op
import sqlalchemy as sa

revision = "0008_concert_images"
down_revision = "0007_concert_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("concert_events", sa.Column("image_url", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("concert_events", "image_url")
