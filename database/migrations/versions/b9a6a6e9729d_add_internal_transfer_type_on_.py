"""Add internal_transfer type on TransactionType

Revision ID: b9a6a6e9729d
Revises: 27eff3691236
Create Date: 2025-08-18 20:59:19.306305

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b9a6a6e9729d'
down_revision = '27eff3691236'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'internal_transfer' value to the TransactionType enum
    op.execute("ALTER TYPE transactiontype ADD VALUE 'internal_transfer'")
    

def downgrade() -> None:
    pass