"""Oylik schyot-fakturalar (invoices, invoice_lines), provider rekvizitlari; yozishma (chat) butunlay olib tashlandi

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-31 12:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

PROVIDER_COLS = [("full_name", 200), ("inn", 9), ("address", 255), ("bank", 150), ("mfo", 5), ("account", 20),
                 ("director", 150), ("chief_accountant", 150)]


def upgrade() -> None:
    # Yozishma olib tashlandi (keyinchalik boshqa formatda qaytishi mumkin)
    op.execute("DELETE FROM user_permissions WHERE code IN ('chat.view', 'chat.write')")
    op.drop_table('chat_reads')
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_index('ix_chat_messages_thread')
    op.drop_table('chat_messages')

    with op.batch_alter_table('providers', schema=None) as batch_op:
        for name, size in PROVIDER_COLS:
            batch_op.add_column(sa.Column(name, sa.String(length=size), nullable=True))

    op.create_table('invoices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=30), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=True),
    sa.Column('period', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('vat', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.Column('sent_by_id', sa.Integer(), nullable=True),
    sa.Column('sms_phone', sa.String(length=30), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_invoices_created_by_id_users')),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_invoices_customer_id_customers')),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_invoices_provider_id_providers')),
    sa.ForeignKeyConstraint(['sent_by_id'], ['users.id'], name=op.f('fk_invoices_sent_by_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invoices')),
    sa.UniqueConstraint('customer_id', 'period', name='uq_invoices_customer_period'),
    sa.UniqueConstraint('number', name=op.f('uq_invoices_number')),
    sa.UniqueConstraint('token', name=op.f('uq_invoices_token'))
    )
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invoices_customer_id'), ['customer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invoices_period'), ['period'], unique=False)

    op.create_table('invoice_lines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('invoice_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('request_id', sa.Integer(), nullable=True),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('qty', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit', sa.String(length=10), nullable=False),
    sa.Column('price', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name=op.f('fk_invoice_lines_invoice_id_invoices'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['request_id'], ['requests.id'], name=op.f('fk_invoice_lines_request_id_requests')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invoice_lines'))
    )
    with op.batch_alter_table('invoice_lines', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invoice_lines_invoice_id'), ['invoice_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('invoice_lines', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invoice_lines_invoice_id'))
    op.drop_table('invoice_lines')
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invoices_period'))
        batch_op.drop_index(batch_op.f('ix_invoices_customer_id'))
    op.drop_table('invoices')
    with op.batch_alter_table('providers', schema=None) as batch_op:
        for name, _ in reversed(PROVIDER_COLS):
            batch_op.drop_column(name)
    # Yozishma jadvallari bo'sh holda qayta yaratiladi (ruxsatlar qaytarilmaydi)
    op.create_table('chat_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('thread_type', sa.String(length=10), nullable=False),
    sa.Column('thread_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('file_key', sa.String(length=200), nullable=True),
    sa.Column('content_type', sa.String(length=50), nullable=True),
    sa.Column('duration_s', sa.Integer(), nullable=True),
    sa.Column('expired', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_chat_messages_author_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_messages'))
    )
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.create_index('ix_chat_messages_thread', ['thread_type', 'thread_id', 'id'], unique=False)
    op.create_table('chat_reads',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('thread_type', sa.String(length=10), nullable=False),
    sa.Column('thread_id', sa.Integer(), nullable=False),
    sa.Column('last_read_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_chat_reads_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'thread_type', 'thread_id', name=op.f('pk_chat_reads'))
    )
