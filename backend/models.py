"""
models.py - Domain Models and SQLAlchemy ORM Entities for Parking Management System.
Faithfully bridges the Object-Oriented Design (OOD) hierarchy from Grokking Reference
with production-grade relational persistence.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from database import Base


# ============================================================================
# 1. ENUMS AND CONSTANTS (Directly from Grokking Reference + Enhancements)
# ============================================================================

class VehicleType(str, Enum):
    CAR = "CAR"
    TRUCK = "TRUCK"
    ELECTRIC = "ELECTRIC"
    VAN = "VAN"
    MOTORBIKE = "MOTORBIKE"


class ParkingSpotType(str, Enum):
    HANDICAPPED = "HANDICAPPED"
    COMPACT = "COMPACT"
    LARGE = "LARGE"
    MOTORBIKE = "MOTORBIKE"
    ELECTRIC = "ELECTRIC"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    BANNED = "BANNED"
    COMPROMISED = "COMPROMISED"
    ARCHIVED = "ARCHIVED"
    UNKNOWN = "UNKNOWN"


class ParkingTicketStatus(str, Enum):
    RESERVED = "RESERVED"  # Reserved online by Customer, awaiting entry
    ACTIVE = "ACTIVE"      # Vehicle checked in at EntrancePanel
    PAID = "PAID"          # Paid and cleared for exit
    LOST = "LOST"          # Ticket reported lost; penalty applied
    EXPIRED = "EXPIRED"    # No-show timeout; spot reclaimed


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"  # Gate Attendant / ParkingAttendant
    CUSTOMER = "CUSTOMER"  # Driver / App User


class SlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentType(str, Enum):
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    UPI_ONLINE = "UPI_ONLINE"
    FASTAG = "FASTAG"


# ============================================================================
# 2. PURE OBJECT-ORIENTED DESIGN HIERARCHY (Grokking Reference Domain Classes)
# ============================================================================

class Address:
    def __init__(self, street: str, city: str, state: str, zip_code: str, country: str):
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.country = country


class Person:
    def __init__(self, name: str, address: Optional[Address], email: str, phone: str):
        self.name = name
        self.address = address
        self.email = email
        self.phone = phone


class Account(ABC):
    def __init__(self, user_name: str, password: str, person: Person, status: AccountStatus = AccountStatus.ACTIVE):
        self.user_name = user_name
        self.password = password
        self.person = person
        self.status = status

    def reset_password(self, new_password: str):
        self.password = new_password


class Admin(Account):
    def __init__(self, user_name: str, password: str, person: Person, status: AccountStatus = AccountStatus.ACTIVE):
        super().__init__(user_name, password, person, status)


class ParkingAttendant(Account):
    def __init__(self, user_name: str, password: str, person: Person, status: AccountStatus = AccountStatus.ACTIVE):
        super().__init__(user_name, password, person, status)


class Customer(Account):
    def __init__(self, user_name: str, password: str, person: Person, status: AccountStatus = AccountStatus.ACTIVE):
        super().__init__(user_name, password, person, status)


class Vehicle(ABC):
    def __init__(self, license_number: str, vehicle_type: VehicleType, ticket=None):
        self.license_number = license_number
        self.vehicle_type = vehicle_type
        self.ticket = ticket

    def assign_ticket(self, ticket):
        self.ticket = ticket


class Car(Vehicle):
    def __init__(self, license_number: str, ticket=None):
        super().__init__(license_number, VehicleType.CAR, ticket)


class Van(Vehicle):
    def __init__(self, license_number: str, ticket=None):
        super().__init__(license_number, VehicleType.VAN, ticket)


class Truck(Vehicle):
    def __init__(self, license_number: str, ticket=None):
        super().__init__(license_number, VehicleType.TRUCK, ticket)


class Motorbike(Vehicle):
    def __init__(self, license_number: str, ticket=None):
        super().__init__(license_number, VehicleType.MOTORBIKE, ticket)


class ElectricCar(Vehicle):
    def __init__(self, license_number: str, ticket=None):
        super().__init__(license_number, VehicleType.ELECTRIC, ticket)


class ParkingSpot(ABC):
    def __init__(self, number: str, parking_spot_type: ParkingSpotType):
        self.number = number
        self.free = True
        self.vehicle: Optional[Vehicle] = None
        self.parking_spot_type = parking_spot_type

    def is_free(self) -> bool:
        return self.free

    def assign_vehicle(self, vehicle: Vehicle):
        self.vehicle = vehicle
        self.free = False

    def remove_vehicle(self):
        self.vehicle = None
        self.free = True


class HandicappedSpot(ParkingSpot):
    def __init__(self, number: str):
        super().__init__(number, ParkingSpotType.HANDICAPPED)


class CompactSpot(ParkingSpot):
    def __init__(self, number: str):
        super().__init__(number, ParkingSpotType.COMPACT)


class LargeSpot(ParkingSpot):
    def __init__(self, number: str):
        super().__init__(number, ParkingSpotType.LARGE)


class MotorbikeSpot(ParkingSpot):
    def __init__(self, number: str):
        super().__init__(number, ParkingSpotType.MOTORBIKE)


class ElectricSpot(ParkingSpot):
    def __init__(self, number: str):
        super().__init__(number, ParkingSpotType.ELECTRIC)


# ============================================================================
# 3. VEHICLE <-> SPOT COMPATIBILITY ENGINE
# ============================================================================

VEHICLE_SPOT_COMPATIBILITY = {
    VehicleType.MOTORBIKE.value: [ParkingSpotType.MOTORBIKE.value, ParkingSpotType.COMPACT.value, ParkingSpotType.LARGE.value],
    VehicleType.CAR.value: [ParkingSpotType.COMPACT.value, ParkingSpotType.LARGE.value],
    VehicleType.VAN.value: [ParkingSpotType.LARGE.value],
    VehicleType.TRUCK.value: [ParkingSpotType.LARGE.value],
    VehicleType.ELECTRIC.value: [ParkingSpotType.ELECTRIC.value, ParkingSpotType.COMPACT.value, ParkingSpotType.LARGE.value],
}

def is_vehicle_compatible(v_type: str, s_type: str) -> tuple[bool, str]:
    """
    Strict business rule enforcement adhering to Grokking Reference OOD:
    - MOTORBIKE -> Allowed in: MOTORBIKE, COMPACT, LARGE
    - CAR -> Allowed in: COMPACT, LARGE
    - VAN -> Allowed in: LARGE
    - TRUCK -> Allowed in: LARGE
    - ELECTRIC -> Allowed in: ELECTRIC, COMPACT, LARGE
    """
    v_type_val = v_type.value if hasattr(v_type, "value") else str(v_type).upper()
    s_type_val = s_type.value if hasattr(s_type, "value") else str(s_type).upper()

    allowed = VEHICLE_SPOT_COMPATIBILITY.get(v_type_val, [ParkingSpotType.COMPACT.value, ParkingSpotType.LARGE.value])
    if s_type_val in allowed:
        return True, "Compatible"
    return False, f"Size Mismatch: Vehicle cannot fit in this stall. Vehicle ({v_type_val}) cannot occupy a {s_type_val} stall."

is_vehicle_compatible_with_spot = is_vehicle_compatible


# ============================================================================
# 4. SQLALCHEMY RELATIONAL DATABASE SCHEMAS
# ============================================================================

class AccountModel(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.CUSTOMER.value)
    status = Column(String(20), nullable=False, default=AccountStatus.ACTIVE.value)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    vehicles = relationship("VehicleModel", back_populates="customer")
    tickets = relationship("ParkingTicketModel", back_populates="customer")


class ParkingLotModel(Base):
    __tablename__ = "parking_lots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Central Grand Parking Lot")
    address = Column(String(255), nullable=False, default="100 Tech Boulevard, Silicon Valley")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    floors = relationship("ParkingFloorModel", back_populates="lot", cascade="all, delete-orphan")


class ParkingFloorModel(Base):
    __tablename__ = "parking_floors"

    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False)
    floor_number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)

    lot = relationship("ParkingLotModel", back_populates="floors")
    spots = relationship("ParkingSpotModel", back_populates="floor", cascade="all, delete-orphan")


class ParkingSpotModel(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    floor_id = Column(Integer, ForeignKey("parking_floors.id"), nullable=False)
    spot_number = Column(String(30), unique=True, index=True, nullable=False)
    spot_type = Column(String(30), nullable=False, default=ParkingSpotType.COMPACT.value)
    status = Column(String(30), nullable=False, default=SlotStatus.AVAILABLE.value)

    floor = relationship("ParkingFloorModel", back_populates="spots")
    tickets = relationship("ParkingTicketModel", back_populates="spot")


class VehicleModel(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(30), nullable=False, default=VehicleType.CAR.value)
    customer_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    customer = relationship("AccountModel", back_populates="vehicles")
    tickets = relationship("ParkingTicketModel", back_populates="vehicle")


class ParkingTicketModel(Base):
    __tablename__ = "parking_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(64), unique=True, index=True, nullable=False)
    spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    entry_time = Column(DateTime, nullable=True)
    booked_start = Column(DateTime, nullable=True)
    booked_end = Column(DateTime, nullable=True)
    actual_exit_time = Column(DateTime, nullable=True)

    status = Column(String(30), nullable=False, default=ParkingTicketStatus.ACTIVE.value)
    base_amount = Column(Float, default=0.0)
    overstay_amount = Column(Float, default=0.0)
    penalty_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    barrier_opened = Column(Boolean, default=False)
    entrance_panel_id = Column(String(50), default="ENTRANCE_PANEL_1")
    exit_panel_id = Column(String(50), nullable=True)
    is_lost_override = Column(Boolean, default=False)
    is_prepaid = Column(Boolean, default=False)
    exit_window_minutes = Column(Integer, default=15)

    spot = relationship("ParkingSpotModel", back_populates="tickets")
    vehicle = relationship("VehicleModel", back_populates="tickets")
    customer = relationship("AccountModel", back_populates="tickets")
    payments = relationship("PaymentModel", back_populates="ticket", cascade="all, delete-orphan")


class ParkingRateModel(Base):
    __tablename__ = "parking_rates"

    id = Column(Integer, primary_key=True, index=True)
    first_hour_rate = Column(Float, default=40.0, nullable=False)
    second_third_hour_rate = Column(Float, default=35.0, nullable=False)
    remaining_hour_rate = Column(Float, default=25.0, nullable=False)
    overstay_multiplier = Column(Float, default=1.5, nullable=False)
    lost_ticket_fee = Column(Float, default=500.0, nullable=False)
    grace_period_minutes = Column(Integer, default=2, nullable=False)
    reservation_hold_minutes = Column(Integer, default=15, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("parking_tickets.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(String(30), nullable=False, default=PaymentType.CASH.value)
    status = Column(String(30), nullable=False, default=PaymentStatus.COMPLETED.value)
    transaction_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reference_id = Column(String(100), nullable=False)

    ticket = relationship("ParkingTicketModel", back_populates="payments")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    actor_username = Column(String(50), nullable=False)
    actor_role = Column(String(30), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=False)
    ip_address = Column(String(50), default="127.0.0.1")
