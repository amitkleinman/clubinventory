"""
Domain models for the club equipment management system.

Tables:
  users                   - system users (COO, Equipment Manager, Admin)
  departments             - Academy, Youth, First Team, Merchandise Shop
  products                - full SKU catalog (name + barcode + color + size + category + brand)
  inventory               - current quantity per product per department
  inventory_movements     - every stock change (IN/OUT/TRANSFER/DAMAGE)
  players                 - squad members with size info
  delivery_notes          - uploaded PDF documents (draft → approved)
  delivery_note_items     - line items extracted from PDF via OCR
  sponsorship_allocations - First Team seasonal quotas per SKU
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum, ForeignKey,
    Integer, String, Text, UniqueConstraint, func, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, gen_uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    COO = "COO"
    EQUIPMENT_MANAGER = "EQUIPMENT_MANAGER"
    ADMIN = "ADMIN"


class DepartmentType(str, enum.Enum):
    ACADEMY = "Academy"
    YOUTH = "Youth"
    FIRST_TEAM = "First Team"
    MERCHANDISE = "Merchandise Shop"


class MovementType(str, enum.Enum):
    IN = "IN"           # from delivery note
    OUT = "OUT"         # issued to player
    TRANSFER = "TRANSFER"  # between departments
    DAMAGE = "DAMAGE"   # lost / damaged


class DeliveryNoteStatus(str, enum.Enum):
    DRAFT = "draft"         # uploaded, OCR pending or done, not yet approved
    PENDING = "pending"     # OCR done, awaiting user confirmation
    APPROVED = "approved"   # confirmed, movements created
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.EQUIPMENT_MANAGER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # relationships
    delivery_notes: Mapped[list["DeliveryNote"]] = relationship(back_populates="created_by_user")
    movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="created_by_user")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    name: Mapped[str] = mapped_column(
        Enum(DepartmentType, name="department_type"), unique=True, nullable=False
    )

    # relationships
    inventory: Mapped[list["Inventory"]] = relationship(back_populates="department")
    players: Mapped[list["Player"]] = relationship(back_populates="department")
    movements: Mapped[list["InventoryMovement"]] = relationship(
        back_populates="department", foreign_keys="InventoryMovement.department_id"
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


# ---------------------------------------------------------------------------
# Products (SKU catalog)
# ---------------------------------------------------------------------------

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    barcode: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(80), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    brand: Mapped[str] = mapped_column(String(80), nullable=False)

    # relationships
    inventory: Mapped[list["Inventory"]] = relationship(back_populates="product")
    movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="product")
    delivery_note_items: Mapped[list["DeliveryNoteItem"]] = relationship(back_populates="product")
    sponsorship_allocations: Mapped[list["SponsorshipAllocation"]] = relationship(
        back_populates="product"
    )

    __table_args__ = (
        Index("ix_products_name_color_size", "product_name", "color", "size"),
    )

    def __repr__(self) -> str:
        return f"<Product {self.product_name} / {self.color} / {self.size}>"


# ---------------------------------------------------------------------------
# Inventory (current stock snapshot)
# ---------------------------------------------------------------------------

class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # relationships
    product: Mapped["Product"] = relationship(back_populates="inventory")
    department: Mapped["Department"] = relationship(back_populates="inventory")

    __table_args__ = (
        UniqueConstraint("product_id", "department_id", name="uq_inventory_product_dept"),
        CheckConstraint("quantity >= 0", name="ck_inventory_qty_non_negative"),
        Index("ix_inventory_dept", "department_id"),
    )

    def __repr__(self) -> str:
        return f"<Inventory product={self.product_id} dept={self.department_id} qty={self.quantity}>"


# ---------------------------------------------------------------------------
# Inventory Movements (immutable ledger)
# ---------------------------------------------------------------------------

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, name="movement_type"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # TRANSFER: target department
    target_department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True
    )

    # OUT: player who received items
    player_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )

    # IN: source delivery note
    delivery_note_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_notes.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    product: Mapped["Product"] = relationship(back_populates="movements")
    department: Mapped["Department"] = relationship(
        back_populates="movements", foreign_keys=[department_id]
    )
    player: Mapped[Optional["Player"]] = relationship(back_populates="movements")
    delivery_note: Mapped[Optional["DeliveryNote"]] = relationship(back_populates="movements")
    created_by_user: Mapped["User"] = relationship(back_populates="movements")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_movement_qty_positive"),
        Index("ix_movement_product_dept", "product_id", "department_id"),
        Index("ix_movement_created_at", "created_at"),
        Index("ix_movement_type", "movement_type"),
    )

    def __repr__(self) -> str:
        return f"<Movement {self.movement_type} qty={self.quantity} product={self.product_id}>"


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    squad_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shirt_size: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    shorts_size: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    shoe_size: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # relationships
    department: Mapped["Department"] = relationship(back_populates="players")
    movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="player")

    __table_args__ = (
        Index("ix_player_department", "department_id"),
    )

    def __repr__(self) -> str:
        return f"<Player {self.name} #{self.squad_number}>"


# ---------------------------------------------------------------------------
# Delivery Notes
# ---------------------------------------------------------------------------

class DeliveryNote(Base, TimestampMixin):
    __tablename__ = "delivery_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    status: Mapped[DeliveryNoteStatus] = mapped_column(
        Enum(DeliveryNoteStatus, name="delivery_note_status"),
        nullable=False,
        default=DeliveryNoteStatus.DRAFT,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO object key

    # supplier info (extracted by OCR)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    document_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # raw OCR output (stored for debugging / re-parsing)
    ocr_raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # relationships
    created_by_user: Mapped["User"] = relationship(
        back_populates="delivery_notes", foreign_keys="[DeliveryNote.created_by]"
    )
    )
    items: Mapped[list["DeliveryNoteItem"]] = relationship(
        back_populates="delivery_note", cascade="all, delete-orphan"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(back_populates="delivery_note")

    __table_args__ = (
        Index("ix_delivery_note_status", "status"),
        Index("ix_delivery_note_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<DeliveryNote {self.original_filename} [{self.status}]>"


class DeliveryNoteItem(Base):
    """One line extracted from the PDF — may or may not be matched to a product."""
    __tablename__ = "delivery_note_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    delivery_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_notes.id", ondelete="CASCADE"), nullable=False
    )

    # matched product (null if OCR couldn't identify it)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # raw data from OCR (kept for manual correction UI)
    matched_barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_product_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    raw_color: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    raw_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_line: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # user confirmed this item (required before approval)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # relationships
    delivery_note: Mapped["DeliveryNote"] = relationship(back_populates="items")
    product: Mapped[Optional["Product"]] = relationship(back_populates="delivery_note_items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_dni_qty_positive"),
        Index("ix_dni_delivery_note", "delivery_note_id"),
    )

    def __repr__(self) -> str:
        return f"<DeliveryNoteItem barcode={self.matched_barcode} qty={self.quantity} confirmed={self.is_confirmed}>"


# ---------------------------------------------------------------------------
# Sponsorship Allocations (First Team only)
# ---------------------------------------------------------------------------

class SponsorshipAllocation(Base, TimestampMixin):
    """
    Seasonal quota per SKU for the First Team.
    allocated_quantity is set manually by the Equipment Manager.
    received_quantity is computed live from IN movements to First Team.
    """
    __tablename__ = "sponsorship_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=gen_uuid
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # relationships
    product: Mapped["Product"] = relationship(back_populates="sponsorship_allocations")

    __table_args__ = (
        UniqueConstraint("product_id", "season_year", name="uq_sponsorship_product_season"),
        CheckConstraint("allocated_quantity >= 0", name="ck_sponsorship_alloc_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<SponsorshipAllocation product={self.product_id} season={self.season_year} alloc={self.allocated_quantity}>"
