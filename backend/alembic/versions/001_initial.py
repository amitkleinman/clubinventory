"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enums ---
    op.execute("CREATE TYPE IF NOT EXISTS user_role AS ENUM ('COO', 'EQUIPMENT_MANAGER', 'ADMIN')")
    op.execute("CREATE TYPE IF NOT EXISTS department_type AS ENUM ('Academy', 'Youth', 'First Team', 'Merchandise Shop')")
    op.execute("CREATE TYPE IF NOT EXISTS movement_type AS ENUM ('IN', 'OUT', 'TRANSFER', 'DAMAGE')")
    op.execute("CREATE TYPE IF NOT EXISTS delivery_note_status AS ENUM ('draft', 'pending', 'approved', 'cancelled')")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("COO", "EQUIPMENT_MANAGER", "ADMIN", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- departments ---
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "name",
            sa.Enum("Academy", "Youth", "First Team", "Merchandise Shop", name="department_type"),
            unique=True,
            nullable=False,
        ),
    )

    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("barcode", sa.String(100), unique=True, nullable=False),
        sa.Column("color", sa.String(80), nullable=False),
        sa.Column("size", sa.String(20), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("brand", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=True)
    op.create_index("ix_products_name_color_size", "products", ["product_name", "color", "size"])

    # --- players ---
    op.create_table(
        "players",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("squad_number", sa.Integer, nullable=True),
        sa.Column("shirt_size", sa.String(10), nullable=True),
        sa.Column("shorts_size", sa.String(10), nullable=True),
        sa.Column("shoe_size", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_player_department", "players", ["department_id"])

    # --- delivery_notes ---
    op.create_table(
        "delivery_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.Enum("draft", "pending", "approved", "cancelled", name="delivery_note_status"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("supplier_name", sa.String(200), nullable=True),
        sa.Column("document_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ocr_raw_json", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_note_status", "delivery_notes", ["status"])
    op.create_index("ix_delivery_note_created_at", "delivery_notes", ["created_at"])

    # --- delivery_note_items ---
    op.create_table(
        "delivery_note_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("delivery_notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("matched_barcode", sa.String(100), nullable=True),
        sa.Column("raw_product_name", sa.String(300), nullable=True),
        sa.Column("raw_color", sa.String(80), nullable=True),
        sa.Column("raw_size", sa.String(20), nullable=True),
        sa.Column("raw_line", sa.Text, nullable=True),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, default=False),
        sa.CheckConstraint("quantity > 0", name="ck_dni_qty_positive"),
    )
    op.create_index("ix_dni_delivery_note", "delivery_note_items", ["delivery_note_id"])

    # --- inventory ---
    op.create_table(
        "inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, default=0),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "department_id", name="uq_inventory_product_dept"),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_qty_non_negative"),
    )
    op.create_index("ix_inventory_dept", "inventory", ["department_id"])

    # --- inventory_movements ---
    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("movement_type", sa.Enum("IN", "OUT", "TRANSFER", "DAMAGE", name="movement_type"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("target_department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("players.id", ondelete="SET NULL"), nullable=True),
        sa.Column("delivery_note_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("delivery_notes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_movement_qty_positive"),
    )
    op.create_index("ix_movement_product_dept", "inventory_movements", ["product_id", "department_id"])
    op.create_index("ix_movement_created_at", "inventory_movements", ["created_at"])
    op.create_index("ix_movement_type", "inventory_movements", ["movement_type"])

    # --- sponsorship_allocations ---
    op.create_table(
        "sponsorship_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("season_year", sa.Integer, nullable=False),
        sa.Column("allocated_quantity", sa.Integer, nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "season_year", name="uq_sponsorship_product_season"),
        sa.CheckConstraint("allocated_quantity >= 0", name="ck_sponsorship_alloc_non_negative"),
    )


def downgrade() -> None:
    op.drop_table("sponsorship_allocations")
    op.drop_table("inventory_movements")
    op.drop_table("inventory")
    op.drop_table("delivery_note_items")
    op.drop_table("delivery_notes")
    op.drop_table("players")
    op.drop_table("products")
    op.drop_table("departments")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS delivery_note_status")
    op.execute("DROP TYPE IF EXISTS movement_type")
    op.execute("DROP TYPE IF EXISTS department_type")
    op.execute("DROP TYPE IF EXISTS user_role")
