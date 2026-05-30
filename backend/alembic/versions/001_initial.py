"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                CREATE TYPE user_role AS ENUM ('COO', 'EQUIPMENT_MANAGER', 'ADMIN');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'department_type') THEN
                CREATE TYPE department_type AS ENUM ('Academy', 'Youth', 'First Team', 'Merchandise Shop');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'movement_type') THEN
                CREATE TYPE movement_type AS ENUM ('IN', 'OUT', 'TRANSFER', 'DAMAGE');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'delivery_note_status') THEN
                CREATE TYPE delivery_note_status AS ENUM ('draft', 'pending', 'approved', 'cancelled');
            END IF;
        END $$;

        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            email VARCHAR(254) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role user_role NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

        CREATE TABLE IF NOT EXISTS departments (
            id UUID PRIMARY KEY,
            name department_type UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id UUID PRIMARY KEY,
            product_name VARCHAR(200) NOT NULL,
            barcode VARCHAR(100) UNIQUE NOT NULL,
            color VARCHAR(80) NOT NULL,
            size VARCHAR(20) NOT NULL,
            category VARCHAR(80) NOT NULL,
            brand VARCHAR(80) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_products_barcode ON products (barcode);
        CREATE INDEX IF NOT EXISTS ix_products_name_color_size ON products (product_name, color, size);

        CREATE TABLE IF NOT EXISTS players (
            id UUID PRIMARY KEY,
            department_id UUID NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
            name VARCHAR(120) NOT NULL,
            squad_number INTEGER,
            shirt_size VARCHAR(10),
            shorts_size VARCHAR(10),
            shoe_size VARCHAR(10),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_player_department ON players (department_id);

        CREATE TABLE IF NOT EXISTS delivery_notes (
            id UUID PRIMARY KEY,
            status delivery_note_status NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(512) NOT NULL,
            supplier_name VARCHAR(200),
            document_date TIMESTAMPTZ,
            ocr_raw_json TEXT,
            created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            approved_at TIMESTAMPTZ,
            approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_delivery_note_status ON delivery_notes (status);
        CREATE INDEX IF NOT EXISTS ix_delivery_note_created_at ON delivery_notes (created_at);

        CREATE TABLE IF NOT EXISTS delivery_note_items (
            id UUID PRIMARY KEY,
            delivery_note_id UUID NOT NULL REFERENCES delivery_notes(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            department_id UUID REFERENCES departments(id) ON DELETE SET NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            matched_barcode VARCHAR(100),
            raw_product_name VARCHAR(300),
            raw_color VARCHAR(80),
            raw_size VARCHAR(20),
            raw_line TEXT,
            is_confirmed BOOLEAN NOT NULL DEFAULT FALSE
        );
        CREATE INDEX IF NOT EXISTS ix_dni_delivery_note ON delivery_note_items (delivery_note_id);

        CREATE TABLE IF NOT EXISTS inventory (
            id UUID PRIMARY KEY,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
            department_id UUID NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
            quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_inventory_product_dept UNIQUE (product_id, department_id)
        );
        CREATE INDEX IF NOT EXISTS ix_inventory_dept ON inventory (department_id);

        CREATE TABLE IF NOT EXISTS inventory_movements (
            id UUID PRIMARY KEY,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
            department_id UUID NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
            movement_type movement_type NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            target_department_id UUID REFERENCES departments(id) ON DELETE RESTRICT,
            player_id UUID REFERENCES players(id) ON DELETE SET NULL,
            delivery_note_id UUID REFERENCES delivery_notes(id) ON DELETE SET NULL,
            created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_movement_product_dept ON inventory_movements (product_id, department_id);
        CREATE INDEX IF NOT EXISTS ix_movement_created_at ON inventory_movements (created_at);
        CREATE INDEX IF NOT EXISTS ix_movement_type ON inventory_movements (movement_type);

        CREATE TABLE IF NOT EXISTS sponsorship_allocations (
            id UUID PRIMARY KEY,
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            season_year INTEGER NOT NULL,
            allocated_quantity INTEGER NOT NULL DEFAULT 0 CHECK (allocated_quantity >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_sponsorship_product_season UNIQUE (product_id, season_year)
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS sponsorship_allocations;
        DROP TABLE IF EXISTS inventory_movements;
        DROP TABLE IF EXISTS inventory;
        DROP TABLE IF EXISTS delivery_note_items;
        DROP TABLE IF EXISTS delivery_notes;
        DROP TABLE IF EXISTS players;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS departments;
        DROP TABLE IF EXISTS users;
        DROP TYPE IF EXISTS delivery_note_status;
        DROP TYPE IF EXISTS movement_type;
        DROP TYPE IF EXISTS department_type;
        DROP TYPE IF EXISTS user_role;
    """)
