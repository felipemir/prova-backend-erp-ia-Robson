"""Initial ERP schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("data_criacao", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('admin', 'employee')", name="ck_employees_role"))
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)
    op.create_table("products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("preco", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantidade_em_estoque", sa.Integer(), nullable=False),
        sa.Column("data_criacao", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("data_atualizacao", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("preco >= 0", name="ck_products_preco_nonnegative"),
        sa.CheckConstraint("quantidade_em_estoque >= 0", name="ck_products_stock_nonnegative"))
    op.create_table("stock_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_key", sa.String(64), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_quantity", sa.Integer(), nullable=False),
        sa.Column("current_quantity", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=False),
        sa.Column("current_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("event_key", name="uq_stock_alert_event_key"))

def downgrade():
    op.drop_table("stock_alerts")
    op.drop_table("products")
    op.drop_index("ix_employees_email", table_name="employees")
    op.drop_table("employees")
