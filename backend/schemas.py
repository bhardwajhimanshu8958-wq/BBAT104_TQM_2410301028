"""
schemas.py - Pydantic v2 schemas for request validation and response serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel, ConfigDict, Field
from models import (
    VehicleType, ParkingSpotType, AccountStatus, ParkingTicketStatus,
    UserRole, SlotStatus, PaymentType, PaymentStatus
)


# ============================================================================
# AUTHENTICATION & USER SCHEMAS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    username: str
    name: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.CUSTOMER
    name: str
    email: str
    phone: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    status: AccountStatus
    name: str
    email: str
    phone: str
    created_at: datetime


# ============================================================================
# INFRASTRUCTURE (FLOORS & SPOTS) SCHEMAS
# ============================================================================

class FloorCreate(BaseModel):
    floor_number: int
    name: str


class SpotCreate(BaseModel):
    floor_id: Optional[int] = None
    floor_number: Optional[int] = None
    spot_number: str
    spot_type: ParkingSpotType


class SpotStatusUpdate(BaseModel):
    status: SlotStatus


class SpotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floor_id: int
    spot_number: str
    spot_type: ParkingSpotType
    status: SlotStatus
    current_license_plate: Optional[str] = None
    current_ticket_number: Optional[str] = None


class FloorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_id: int
    floor_number: int
    name: str
    spots: List[SpotResponse] = []


# ============================================================================
# PARKING RATES SCHEMAS
# ============================================================================

class RateUpdate(BaseModel):
    first_hour_rate: float = Field(..., gt=0, description="Base rate for the 1st hour")
    second_third_hour_rate: float = Field(..., gt=0, description="Hourly rate for 2nd and 3rd hours")
    remaining_hour_rate: float = Field(..., gt=0, description="Hourly rate for 4th hour onwards")
    overstay_multiplier: float = Field(..., ge=1.0, description="Penalty multiplier applied on excess hours")
    lost_ticket_fee: float = Field(..., gt=0, description="Flat penalty fee for lost ticket overrides")
    grace_period_minutes: int = Field(..., ge=0, description="Free exit grace period for immediate turnaround")
    reservation_hold_minutes: int = Field(..., ge=1, description="Grace window before unclaimed reservations expire")


class RateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_hour_rate: float
    second_third_hour_rate: float
    remaining_hour_rate: float
    overstay_multiplier: float
    lost_ticket_fee: float
    grace_period_minutes: int
    reservation_hold_minutes: int
    updated_at: datetime


# ============================================================================
# TICKET, RESERVATION & CHECKOUT SCHEMAS
# ============================================================================

class ReservationRequest(BaseModel):
    spot_id: Optional[Any] = None
    slot_id: Optional[Any] = None
    license_plate: Optional[str] = None
    plate_number: Optional[str] = None
    plate: Optional[str] = None
    vehicle_type: Optional[Any] = "CAR"
    duration_hours: Optional[Any] = 2

    class Config:
        extra = "allow"


class CheckInRequest(BaseModel):
    ticket_number: Optional[str] = None
    license_plate: Optional[str] = None
    vehicle_type: VehicleType = VehicleType.CAR
    spot_id: Optional[int] = None
    entrance_panel_id: str = "ENTRANCE_PANEL_1"


class FeeCalculationResponse(BaseModel):
    ticket_number: str
    license_plate: str
    spot_number: str
    vehicle_type: str
    entry_time: datetime
    exit_time: datetime
    duration_minutes: int
    is_grace_period: bool
    base_hours: int
    base_fee: float
    excess_hours: int
    overstay_multiplier: float
    overstay_fee: float
    lost_ticket_fee: float
    total_amount: float
    status: str
    message: str


class CheckOutRequest(BaseModel):
    ticket_number: str
    exit_panel_id: str = "EXIT_PANEL_1"
    payment_type: PaymentType = PaymentType.CASH


class LostTicketRequest(BaseModel):
    license_plate: str
    exit_panel_id: str = "EXIT_PANEL_1"
    payment_type: PaymentType = PaymentType.CASH


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    spot_id: int
    spot_number: Optional[str] = None
    floor_name: Optional[str] = None
    license_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    issued_at: datetime
    entry_time: Optional[datetime] = None
    booked_start: Optional[datetime] = None
    booked_end: Optional[datetime] = None
    actual_exit_time: Optional[datetime] = None
    status: ParkingTicketStatus
    base_amount: float
    overstay_amount: float
    penalty_amount: float
    total_amount: float
    barrier_opened: bool
    entrance_panel_id: str
    exit_panel_id: Optional[str] = None
    is_lost_override: bool
    is_prepaid: bool = False
    exit_window_minutes: Optional[int] = 15


# ============================================================================
# PARKING DISPLAY BOARD & AUDIT SCHEMAS
# ============================================================================

class TypeAvailability(BaseModel):
    total: int
    free: int
    occupied: int
    reserved: int


class FloorDisplayBoardResponse(BaseModel):
    floor_id: int
    floor_number: int
    floor_name: str
    total_spots: int
    free_spots: int
    reserved_spots: int
    occupied_spots: int
    availability_by_type: Dict[str, TypeAvailability]


class BarrierControlRequest(BaseModel):
    panel_id: str = "GATE_BARRIER_1"
    action: str = Field(..., description="'OPEN' or 'CLOSE'")


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    actor_username: str
    actor_role: str
    action: str
    details: str
    ip_address: Optional[str] = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    license_plate: str
    amount: float
    payment_type: str
    status: str
    reference_id: str
    transaction_time: datetime
    operator: Optional[str] = "Station #04 POS"


class IncidentLogRequest(BaseModel):
    incident_type: str
    license_plate: Optional[str] = None
    stall_number: Optional[str] = None
    notes: str


# ============================================================================
# SUPERVISOR ADVANCED SIMULATION SCHEMAS
# ============================================================================

class ConcurrencyAttemptRequest(BaseModel):
    spot_id: int
    request_id: Union[str, int] = "REQ-1"
    license_plate: str
    vehicle_type: VehicleType = VehicleType.CAR


class OverstaySimulationRequest(BaseModel):
    ticket_code: Optional[str] = None
    ticket_number: Optional[str] = None
    hours_added: Optional[float] = 3.0


class LostTicketOverrideRequest(BaseModel):
    license_plate: str = "UNKNOWN-VEHICLE"
    payment_type: Optional[PaymentType] = None
    payment_method: Optional[str] = "CASH"


class QuarantineFloorRequest(BaseModel):
    floor: Optional[Any] = None
    floor_number: Optional[Any] = 1
    reason: Optional[str] = "Emergency Sector Quarantine"

    class Config:
        extra = "allow"

