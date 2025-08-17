"""Add status fields on ReferralCommission and Transaction table

Revision ID: 27eff3691236
Revises: ad7bbeaf593f
Create Date: 2025-08-17 08:18:27.000953

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '27eff3691236'
down_revision = 'ad7bbeaf593f'
branch_labels = None
depends_on = None

# Explicit ENUM definitions
commission_status = sa.Enum('pending', 'paid', name='commissionstatus')
transaction_status = sa.Enum('pending', 'completed', 'failed', name='transactionstatus')

def upgrade() -> None:
    # Create ENUM types before using them
    commission_status.create(op.get_bind(), checkfirst=True)
    transaction_status.create(op.get_bind(), checkfirst=True)

    # Add new columns with default value to avoid errors if rows already exist
    op.add_column(
        'referral_commissions',
        sa.Column('status', commission_status, nullable=False, server_default='pending')
    )
    op.add_column(
        'transactions',
        sa.Column('status', transaction_status, nullable=False, server_default='pending')
    )


def downgrade() -> None:
    # Drop columns first
    op.drop_column('transactions', 'status')
    op.drop_column('referral_commissions', 'status')

    # Drop ENUM types explicitly
    transaction_status.drop(op.get_bind(), checkfirst=True)
    commission_status.drop(op.get_bind(), checkfirst=True)

    # Recreate apscheduler_jobs table (rollback safety)
    op.create_table(
        'apscheduler_jobs',
        sa.Column('id', sa.VARCHAR(length=191), autoincrement=False, nullable=False),
        sa.Column('next_run_time', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column('job_state', postgresql.BYTEA(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('apscheduler_jobs_pkey')),
        if_not_exists=True,
    )
    op.create_index(op.f('ix_apscheduler_jobs_next_run_time'), 'apscheduler_jobs', ['next_run_time'], unique=False, if_not_exists=True)