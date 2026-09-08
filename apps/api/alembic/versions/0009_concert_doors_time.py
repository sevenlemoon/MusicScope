"""Store concert doors/opening time."""

from alembic import op
import sqlalchemy as sa

revision = "0009_concert_doors_time"
down_revision = "0008_concert_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("concert_events", sa.Column("doors_time", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("concert_events", "doors_time")
