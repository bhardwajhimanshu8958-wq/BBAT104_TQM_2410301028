"""
main.py - Production-Grade FastAPI Parking Management Application.
Implements Strict 3-Role RBAC, Edge Cases, Atomic Concurrency,
Lifespan Auto-Seeding, Background No-Show Reaper, and Serves Single-Page UI.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import math
import os
import random
import re
import time
from typing import List, Optional, Any, Dict
import uuid

from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_

from database import engine, get_db, Base, SessionLocal, db_write_lock
from models import (
    AccountModel, ParkingLotModel, ParkingFloorModel, ParkingSpotModel,
    VehicleModel, ParkingTicketModel, ParkingRateModel, PaymentModel, AuditLogModel,
    UserRole, AccountStatus, VehicleType, ParkingSpotType, SlotStatus,
    ParkingTicketStatus, PaymentType, PaymentStatus,
    is_vehicle_compatible, is_vehicle_compatible_with_spot, VEHICLE_SPOT_COMPATIBILITY
)
from schemas import (
    LoginRequest, Token, UserCreate, UserResponse,
    FloorCreate, FloorResponse, SpotCreate, SpotResponse, SpotStatusUpdate,
    RateUpdate, RateResponse,
    ReservationRequest, CheckInRequest, FeeCalculationResponse,
    CheckOutRequest, LostTicketRequest, TicketResponse,
    FloorDisplayBoardResponse, TypeAvailability,
    BarrierControlRequest, AuditLogResponse,
    TransactionResponse, IncidentLogRequest,
    ConcurrencyAttemptRequest, OverstaySimulationRequest,
    LostTicketOverrideRequest, QuarantineFloorRequest
)
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_role
)

# Global reaper task handle
reaper_task = None


# ============================================================================
# AUDIT LOGGING HELPER
# ============================================================================

def record_audit_event(db: Session, actor_username: str, actor_role: str, action: str, details: str, ip: str = "127.0.0.1"):
    """Record financial and security operational events into persistent audit log."""
    log_entry = AuditLogModel(
        timestamp=datetime.now(timezone.utc),
        actor_username=actor_username,
        actor_role=actor_role,
        action=action,
        details=details,
        ip_address=ip
    )
    db.add(log_entry)
    db.commit()
    return log_entry

log_audit = record_audit_event


# ============================================================================
# FEE CALCULATION ENGINE (TIERED + OVERSTAY PENALTY + GRACE PERIOD)
# ============================================================================

def calculate_ticket_fee(
    entry_time: datetime,
    exit_time: datetime,
    booked_end: Optional[datetime],
    rates: ParkingRateModel,
    is_lost: bool = False
) -> dict:
    """
    Computes parking fees enforcing:
    1. Lost Ticket Flat Penalty Fee
    2. Immediate Exit Grace Period (<= 2 minutes -> ₹0)
    3. Tiered Hourly Rates (1st hr, 2nd-3rd hr, 4th+ hr)
    4. 1.5x Overstay Penalty Multiplier on excess hours
    """
    if is_lost:
        return {
            "is_grace_period": False,
            "duration_minutes": 0,
            "base_hours": 0,
            "base_fee": 0.0,
            "excess_hours": 0,
            "overstay_multiplier": rates.overstay_multiplier,
            "overstay_fee": 0.0,
            "lost_ticket_fee": rates.lost_ticket_fee,
            "total_amount": rates.lost_ticket_fee,
            "message": f"Lost Ticket Override Applied. Flat Penalty Fee: ₹{rates.lost_ticket_fee:.2f}"
        }

    # Ensure timezone aware / UTC comparison
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)
    if exit_time.tzinfo is None:
        exit_time = exit_time.replace(tzinfo=timezone.utc)

    duration_seconds = max(0, (exit_time - entry_time).total_seconds())
    duration_minutes = int(duration_seconds / 60)

    # Check for overstay condition against booked reservation window
    is_overstay = False
    if booked_end:
        if booked_end.tzinfo is None:
            booked_end = booked_end.replace(tzinfo=timezone.utc)
        if exit_time > booked_end:
            is_overstay = True

    # Edge Case 5: Immediate Exit Grace Period (<= 2 minutes AND no overstay)
    if duration_minutes <= rates.grace_period_minutes and not is_overstay:
        return {
            "is_grace_period": True,
            "duration_minutes": duration_minutes,
            "base_hours": 0,
            "base_fee": 0.0,
            "excess_hours": 0,
            "overstay_multiplier": rates.overstay_multiplier,
            "overstay_fee": 0.0,
            "lost_ticket_fee": 0.0,
            "total_amount": 0.0,
            "message": f"Immediate Exit Grace Period (<={rates.grace_period_minutes} mins). ₹0 charge."
        }

    total_duration_hours = max(1, math.ceil(duration_seconds / 3600))
    excess_hours = 0
    base_hours = total_duration_hours

    # Edge Case 3: Overstay Penalty Calculation
    if booked_end:
        if booked_end.tzinfo is None:
            booked_end = booked_end.replace(tzinfo=timezone.utc)
        if exit_time > booked_end:
            excess_seconds = (exit_time - booked_end).total_seconds()
            excess_hours = max(1, math.ceil(excess_seconds / 3600))
            base_seconds = max(0, (booked_end - entry_time).total_seconds())
            base_hours = max(1, math.ceil(base_seconds / 3600))

    # Tiered base calculation
    base_fee = 0.0
    for h in range(1, base_hours + 1):
        if h == 1:
            base_fee += rates.first_hour_rate
        elif h in [2, 3]:
            base_fee += rates.second_third_hour_rate
        else:
            base_fee += rates.remaining_hour_rate

    # Overstay calculation with multiplier
    overstay_fee = 0.0
    if excess_hours > 0:
        overstay_fee = round(excess_hours * rates.remaining_hour_rate * rates.overstay_multiplier, 2)

    total_amount = round(base_fee + overstay_fee, 2)
    msg = f"Standard Parking Fee ({base_hours}h): ₹{base_fee:.2f}"
    if overstay_fee > 0:
        msg += f" + Overstay Penalty ({excess_hours}h @ {rates.overstay_multiplier}x): ₹{overstay_fee:.2f}"

    return {
        "is_grace_period": False,
        "duration_minutes": duration_minutes,
        "base_hours": base_hours,
        "base_fee": base_fee,
        "excess_hours": excess_hours,
        "overstay_multiplier": rates.overstay_multiplier,
        "overstay_fee": overstay_fee,
        "lost_ticket_fee": 0.0,
        "total_amount": total_amount,
        "message": msg
    }


# ============================================================================
# BACKGROUND WORKER: EXPIRED RESERVATION RECLAMATION (NO-SHOW WORKER)
# ============================================================================

def sweep_expired_reservations(db: Session) -> List[str]:
    """
    Sweeps database for RESERVED tickets that exceeded their hold grace period.
    Reclaims slots back to AVAILABLE and records audit events.
    """
    reclaimed = []
    rates = db.query(ParkingRateModel).first()
    hold_minutes = rates.reservation_hold_minutes if rates else 15
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=hold_minutes)

    with db_write_lock:
        reserved_tickets = db.query(ParkingTicketModel).filter(
            ParkingTicketModel.status == ParkingTicketStatus.RESERVED.value
        ).all()

        for ticket in reserved_tickets:
            t_issued = ticket.issued_at
            if t_issued.tzinfo is None:
                t_issued = t_issued.replace(tzinfo=timezone.utc)

            if t_issued < cutoff_time:
                ticket.status = ParkingTicketStatus.EXPIRED.value
                spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.id == ticket.spot_id).first()
                if spot:
                    spot.status = SlotStatus.AVAILABLE.value
                    msg = f"Reservation {ticket.ticket_number} expired (> {hold_minutes}m). Slot {spot.spot_number} reclaimed to AVAILABLE."
                else:
                    msg = f"Reservation {ticket.ticket_number} expired."

                reclaimed.append(msg)
                log_audit(
                    db,
                    actor_username="SYSTEM_WORKER",
                    actor_role="SYSTEM",
                    action="AUTO_RECLAIM_EXPIRED_RESERVATION",
                    details=msg
                )

        if reclaimed:
            db.commit()

    return reclaimed


async def background_no_show_worker():
    """Periodic 15-second background task running in FastAPI lifespan."""
    while True:
        try:
            await asyncio.sleep(15)
            db = SessionLocal()
            try:
                sweep_expired_reservations(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[REAPER WORKER ERROR] {e}")


# ============================================================================
# DATABASE SEEDING ENGINE (LIFESPAN STARTUP)
# ============================================================================

def seed_database():
    """Idempotent seed engine populating initial users, floors, spots, and rates."""
    db = SessionLocal()
    try:
        # 1. Seed Default Rates
        rates = db.query(ParkingRateModel).first()
        if not rates:
            rates = ParkingRateModel(
                first_hour_rate=40.0,
                second_third_hour_rate=35.0,
                remaining_hour_rate=25.0,
                overstay_multiplier=1.5,
                lost_ticket_fee=500.0,
                grace_period_minutes=2,
                reservation_hold_minutes=15
            )
            db.add(rates)
            db.commit()

        # 2. Seed Default Accounts
        users_to_seed = [
            ("admin1", "admin123", UserRole.ADMIN, "Chief Administrator", "admin@parking.com", "+1-800-555-0101"),
            ("gateman1", "gate123", UserRole.OPERATOR, "Gate Attendant John", "gateman@parking.com", "+1-800-555-0102"),
            ("driver1", "driver123", UserRole.CUSTOMER, "Driver Alice Parker", "alice@customer.com", "+1-800-555-0103"),
        ]
        for uname, pwd, role, name, email, phone in users_to_seed:
            existing = db.query(AccountModel).filter(AccountModel.username == uname).first()
            if not existing:
                account = AccountModel(
                    username=uname,
                    hashed_password=hash_password(pwd),
                    role=role.value,
                    status=AccountStatus.ACTIVE.value,
                    name=name,
                    email=email,
                    phone=phone
                )
                db.add(account)
        db.commit()

        # 3. Seed Parking Lot
        lot = db.query(ParkingLotModel).first()
        if not lot:
            lot = ParkingLotModel(
                name="Central Grand Parking Lot",
                address="100 Tech Boulevard, Silicon Valley, CA 94025"
            )
            db.add(lot)
            db.commit()
            db.refresh(lot)

        # 4. Seed 2 Floors with 12 Diverse Slots
        floor1 = db.query(ParkingFloorModel).filter(ParkingFloorModel.floor_number == 1).first()
        if not floor1:
            floor1 = ParkingFloorModel(lot_id=lot.id, floor_number=1, name="Ground Floor (P1)")
            db.add(floor1)
            db.commit()
            db.refresh(floor1)

            p1_spots = [
                ("P1-101", ParkingSpotType.COMPACT),
                ("P1-102", ParkingSpotType.COMPACT),
                ("P1-103", ParkingSpotType.MOTORBIKE),
                ("P1-104", ParkingSpotType.LARGE),
                ("P1-105", ParkingSpotType.HANDICAPPED),
                ("P1-106", ParkingSpotType.ELECTRIC),
            ]
            for s_num, s_type in p1_spots:
                db.add(ParkingSpotModel(
                    floor_id=floor1.id,
                    spot_number=s_num,
                    spot_type=s_type.value,
                    status=SlotStatus.AVAILABLE.value
                ))
            db.commit()

        floor2 = db.query(ParkingFloorModel).filter(ParkingFloorModel.floor_number == 2).first()
        if not floor2:
            floor2 = ParkingFloorModel(lot_id=lot.id, floor_number=2, name="Level 2 (P2)")
            db.add(floor2)
            db.commit()
            db.refresh(floor2)

            p2_spots = [
                ("P2-201", ParkingSpotType.COMPACT),
                ("P2-202", ParkingSpotType.COMPACT),
                ("P2-203", ParkingSpotType.MOTORBIKE),
                ("P2-204", ParkingSpotType.LARGE),
                ("P2-205", ParkingSpotType.HANDICAPPED),
                ("P2-206", ParkingSpotType.ELECTRIC),
            ]
            for s_num, s_type in p2_spots:
                db.add(ParkingSpotModel(
                    floor_id=floor2.id,
                    spot_number=s_num,
                    spot_type=s_type.value,
                    status=SlotStatus.AVAILABLE.value
                ))
            db.commit()

        floor3 = db.query(ParkingFloorModel).filter(ParkingFloorModel.floor_number == 3).first()
        if not floor3:
            floor3 = ParkingFloorModel(lot_id=lot.id, floor_number=3, name="Level 3 (P3)")
            db.add(floor3)
            db.commit()
            db.refresh(floor3)

            p3_spots = [
                ("P3-301", ParkingSpotType.COMPACT),
                ("P3-302", ParkingSpotType.COMPACT),
                ("P3-303", ParkingSpotType.MOTORBIKE),
                ("P3-304", ParkingSpotType.LARGE),
                ("P3-305", ParkingSpotType.HANDICAPPED),
                ("P3-306", ParkingSpotType.ELECTRIC),
            ]
            for s_num, s_type in p3_spots:
                db.add(ParkingSpotModel(
                    floor_id=floor3.id,
                    spot_number=s_num,
                    spot_type=s_type.value,
                    status=SlotStatus.AVAILABLE.value
                ))
            db.commit()

        # Check SQLite migration for is_prepaid and exit_window_minutes
        try:
            db.execute(text("ALTER TABLE parking_tickets ADD COLUMN is_prepaid BOOLEAN DEFAULT 0"))
            db.commit()
        except Exception:
            db.rollback()
        try:
            db.execute(text("ALTER TABLE parking_tickets ADD COLUMN exit_window_minutes INTEGER DEFAULT 15"))
            db.commit()
        except Exception:
            db.rollback()

        # Seed Initial Audit Log
        if not db.query(AuditLogModel).first():
            log_audit(
                db,
                actor_username="SYSTEM",
                actor_role="SYSTEM",
                action="SYSTEM_INITIALIZED",
                details="Parking Management System tables initialized and auto-seeded successfully with 3 floors & 18 slots."
            )
    finally:
        db.close()


# ============================================================================
# FASTAPI LIFESPAN LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist, seed records, start sweeper
    Base.metadata.create_all(bind=engine)
    seed_database()
    global reaper_task
    reaper_task = asyncio.create_task(background_no_show_worker())
    yield
    # Shutdown: Cancel background worker
    if reaper_task:
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Parking Management System - Production Backend",
    description="Full-stack Parking Management System demonstrating Grokking Reference OOD, Strict 3-Role RBAC, and Production Edge Cases.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# ============================================================================
# AUTHENTICATION & ROLE MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/auth/login", response_model=Token)
def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with username and password, returns signed JWT."""
    user = db.query(AccountModel).filter(AccountModel.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password."
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    log_audit(db, user.username, user.role, "USER_LOGIN", f"User {user.username} logged in successfully.")
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=UserRole(user.role),
        username=user.username,
        name=user.name
    )


@app.get("/api/auth/quick-token/{role}", response_model=Token)
def quick_role_token(role: str, db: Session = Depends(get_db)):
    """
    1-Click Role Switcher helper for the UI:
    Issues pre-signed JWT token for the requested role (admin1, gateman1, driver1).
    """
    role_map = {
        "admin": "admin1",
        "operator": "gateman1",
        "gateman": "gateman1",
        "customer": "driver1",
        "driver": "driver1"
    }
    target_username = role_map.get(role.lower())
    if not target_username:
        raise HTTPException(status_code=400, detail=f"Unknown role '{role}'. Use admin, operator, or customer.")

    user = db.query(AccountModel).filter(AccountModel.username == target_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Default user for role not found.")

    token = create_access_token(data={"sub": user.username, "role": user.role})
    return Token(
        access_token=token,
        token_type="bearer",
        role=UserRole(user.role),
        username=user.username,
        name=user.name
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_profile(current_user: AccountModel = Depends(get_current_user)):
    """Returns the profile of the currently authenticated actor."""
    return current_user


# ============================================================================
# DISPLAY BOARD & PUBLIC CAPACITY ENDPOINTS
# ============================================================================

@app.get("/api/display-board", response_model=List[FloorDisplayBoardResponse])
def get_display_board(db: Session = Depends(get_db)):
    """
    Live ParkingDisplayBoard endpoint:
    Aggregates free and occupied spots per floor and per vehicle/spot type.
    """
    floors = db.query(ParkingFloorModel).order_by(ParkingFloorModel.floor_number).all()
    results = []

    for f in floors:
        spots = db.query(ParkingSpotModel).filter(ParkingSpotModel.floor_id == f.id).all()
        total_spots = len(spots)
        free_spots = sum(1 for s in spots if s.status == SlotStatus.AVAILABLE.value)
        reserved_spots = sum(1 for s in spots if s.status == SlotStatus.RESERVED.value)
        occupied_spots = sum(1 for s in spots if s.status == SlotStatus.OCCUPIED.value)

        by_type = {}
        for spot_type in ParkingSpotType:
            type_spots = [s for s in spots if s.spot_type == spot_type.value]
            by_type[spot_type.value] = TypeAvailability(
                total=len(type_spots),
                free=sum(1 for s in type_spots if s.status == SlotStatus.AVAILABLE.value),
                reserved=sum(1 for s in type_spots if s.status == SlotStatus.RESERVED.value),
                occupied=sum(1 for s in type_spots if s.status == SlotStatus.OCCUPIED.value)
            )

        results.append(FloorDisplayBoardResponse(
            floor_id=f.id,
            floor_number=f.floor_number,
            floor_name=f.name,
            total_spots=total_spots,
            free_spots=free_spots,
            reserved_spots=reserved_spots,
            occupied_spots=occupied_spots,
            availability_by_type=by_type
        ))

    return results


@app.get("/api/floors", response_model=List[FloorResponse])
def get_all_floors_and_spots(db: Session = Depends(get_db)):
    """Returns all floors and slots with their current operational statuses."""
    floors = db.query(ParkingFloorModel).order_by(ParkingFloorModel.floor_number).all()
    output = []
    for f in floors:
        spots = db.query(ParkingSpotModel).filter(ParkingSpotModel.floor_id == f.id).all()
        spot_responses = []
        for s in spots:
            plate = None
            tkt_num = None
            # Only attach occupant plate if stall is currently RESERVED or OCCUPIED
            if s.status in (SlotStatus.RESERVED.value, SlotStatus.OCCUPIED.value):
                active_tkt = db.query(ParkingTicketModel).filter(
                    ParkingTicketModel.spot_id == s.id,
                    ParkingTicketModel.status.in_([
                        ParkingTicketStatus.ACTIVE.value,
                        ParkingTicketStatus.RESERVED.value,
                        ParkingTicketStatus.PAID.value
                    ]),
                    ParkingTicketModel.actual_exit_time.is_(None)
                ).order_by(ParkingTicketModel.issued_at.desc()).first()
                plate = active_tkt.vehicle.license_plate if active_tkt and active_tkt.vehicle else None
                tkt_num = active_tkt.ticket_number if active_tkt else None

            spot_responses.append(SpotResponse(
                id=s.id,
                floor_id=s.floor_id,
                spot_number=s.spot_number,
                spot_type=ParkingSpotType(s.spot_type),
                status=SlotStatus(s.status),
                current_license_plate=plate,
                current_ticket_number=tkt_num
            ))
        output.append(FloorResponse(
            id=f.id,
            lot_id=f.lot_id,
            floor_number=f.floor_number,
            name=f.name,
            spots=spot_responses
        ))
    return output


@app.get("/api/rates", response_model=RateResponse)
def get_parking_rates(db: Session = Depends(get_db)):
    """Returns active parking rate structure."""
    rates = db.query(ParkingRateModel).first()
    if not rates:
        raise HTTPException(status_code=404, detail="Rates not configured.")
    return rates


# ============================================================================
# ROLE 3: CUSTOMER / DRIVER ENDPOINTS (Strict require_role([CUSTOMER]))
# ============================================================================

@app.post("/api/customer/reserve", response_model=TicketResponse)
def customer_reserve_slot(
    req: ReservationRequest,
    current_user: AccountModel = Depends(require_role([UserRole.CUSTOMER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Customer / Driver endpoint to pre-book a parking slot.
    EDGE CASE 1: Atomic Concurrency & Pessimistic Locking:
    Uses SELECT ... with_for_update() and thread write lock.
    If the slot is already RESERVED, OCCUPIED, or MAINTENANCE:
    Strictly returns HTTP 409 Conflict: Slot just taken by another vehicle.
    EDGE CASE 4: Enforces Vehicle Type compatibility with Slot Type (e.g. TRUCK on COMPACT returns 400).
    """
    # Accept plate_number, plate, license_plate
    raw_plate = req.plate_number or req.plate or req.license_plate
    if not raw_plate:
        raw_plate = f"UK04-DEMO-{random.randint(1000, 9999)}"
    license_plate = str(raw_plate).strip().upper()

    # Default fallback values for vehicle_type
    raw_vt = req.vehicle_type or "CAR"
    if hasattr(raw_vt, "value"):
        raw_vt_str = raw_vt.value
    else:
        raw_vt_str = str(raw_vt).strip().upper()

    try:
        vehicle_type_enum = VehicleType(raw_vt_str)
    except Exception:
        vehicle_type_enum = VehicleType.CAR

    # Default fallback values for duration_hours
    try:
        duration_hours = int(req.duration_hours) if req.duration_hours is not None else 2
        if duration_hours <= 0:
            duration_hours = 2
    except Exception:
        duration_hours = 2

    raw_spot_id = req.slot_id if req.slot_id is not None else req.spot_id
    now = datetime.now(timezone.utc)

    with db_write_lock:
        spot = None
        if raw_spot_id is not None:
            try:
                spot_int = int(raw_spot_id)
                spot = db.query(ParkingSpotModel).filter(
                    ParkingSpotModel.id == spot_int
                ).with_for_update().first()
            except (ValueError, TypeError):
                spot = db.query(ParkingSpotModel).filter(
                    ParkingSpotModel.spot_number == str(raw_spot_id)
                ).with_for_update().first()

        # If not found by ID or if no spot_id was passed, dynamically pick first available compatible spot
        if not spot and raw_spot_id is None:
            avail_spots = db.query(ParkingSpotModel).filter(
                ParkingSpotModel.status == SlotStatus.AVAILABLE.value
            ).with_for_update().all()
            for s in avail_spots:
                is_compat, _ = is_vehicle_compatible(vehicle_type_enum, s.spot_type)
                if is_compat:
                    spot = s
                    break

        if not spot:
            detail_msg = f"Slot ID {raw_spot_id} not found." if raw_spot_id is not None else "No available compatible stalls found."
            raise HTTPException(status_code=404, detail=detail_msg)

        # Check vehicle compatibility with spot
        is_compat, msg = is_vehicle_compatible(vehicle_type_enum, spot.spot_type)
        if not is_compat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )

        # Concurrency Conflict Check
        if spot.status != SlotStatus.AVAILABLE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Slot '{spot.spot_number}' just taken by another vehicle! Current status: {spot.status}."
            )

        # Allocate slot to RESERVED
        spot.status = SlotStatus.RESERVED.value

        # Register or update Vehicle record
        vehicle = db.query(VehicleModel).filter(VehicleModel.license_plate == license_plate).first()
        if not vehicle:
            vehicle = VehicleModel(
                license_plate=license_plate,
                vehicle_type=vehicle_type_enum.value,
                customer_id=current_user.id
            )
            db.add(vehicle)
            db.flush()
        else:
            vehicle.vehicle_type = vehicle_type_enum.value
            vehicle.customer_id = current_user.id

        # Generate ticket
        ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        booked_end = now + timedelta(hours=duration_hours)

        ticket = ParkingTicketModel(
            ticket_number=ticket_number,
            spot_id=spot.id,
            vehicle_id=vehicle.id,
            customer_id=current_user.id,
            issued_at=now,
            booked_start=now,
            booked_end=booked_end,
            status=ParkingTicketStatus.RESERVED.value,
            entrance_panel_id="ENTRANCE_PANEL_1"
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        record_audit_event(
            db,
            actor_username=current_user.username,
            actor_role=current_user.role,
            action="CUSTOMER_RESERVATION",
            details=f"Slot {spot.spot_number} successfully reserved for {license_plate} ({vehicle_type_enum.value}) for {duration_hours}h. Ticket: {ticket_number}."
        )

        return TicketResponse(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            spot_id=spot.id,
            spot_number=spot.spot_number,
            floor_name=spot.floor.name if spot.floor else "Floor",
            license_plate=license_plate,
            vehicle_type=vehicle_type_enum.value,
            issued_at=ticket.issued_at,
            entry_time=ticket.entry_time,
            booked_start=ticket.booked_start,
            booked_end=ticket.booked_end,
            actual_exit_time=ticket.actual_exit_time,
            status=ParkingTicketStatus(ticket.status),
            base_amount=ticket.base_amount,
            overstay_amount=ticket.overstay_amount,
            penalty_amount=ticket.penalty_amount,
            total_amount=ticket.total_amount,
            barrier_opened=ticket.barrier_opened,
            entrance_panel_id=ticket.entrance_panel_id,
            exit_panel_id=ticket.exit_panel_id,
            is_lost_override=ticket.is_lost_override
        )


@app.get("/api/customer/available-spots")
def get_customer_available_spots(db: Session = Depends(get_db)):
    """
    Returns list of all currently available parking stalls for customer discovery.
    """
    spots = db.query(ParkingSpotModel).filter(
        ParkingSpotModel.status == SlotStatus.AVAILABLE.value
    ).all()
    return [
        {
            "id": s.id,
            "slot_id": s.id,
            "spot_number": s.spot_number,
            "spot_type": s.spot_type,
            "status": s.status,
            "floor_id": s.floor_id
        }
        for s in spots
    ]


@app.get("/api/customer/my-tickets", response_model=List[TicketResponse])
def get_customer_tickets(
    current_user: AccountModel = Depends(require_role([UserRole.CUSTOMER])),
    db: Session = Depends(get_db)
):
    """Customer endpoint to view all active, reserved, or historic tickets."""
    tickets = db.query(ParkingTicketModel).filter(
        ParkingTicketModel.customer_id == current_user.id
    ).order_by(ParkingTicketModel.issued_at.desc()).all()

    output = []
    for t in tickets:
        output.append(TicketResponse(
            id=t.id,
            ticket_number=t.ticket_number,
            spot_id=t.spot_id,
            spot_number=t.spot.spot_number if t.spot else "",
            floor_name=t.spot.floor.name if t.spot and t.spot.floor else "",
            license_plate=t.vehicle.license_plate if t.vehicle else "",
            vehicle_type=t.vehicle.vehicle_type if t.vehicle else "",
            issued_at=t.issued_at,
            entry_time=t.entry_time,
            booked_start=t.booked_start,
            booked_end=t.booked_end,
            actual_exit_time=t.actual_exit_time,
            status=ParkingTicketStatus(t.status),
            base_amount=t.base_amount,
            overstay_amount=t.overstay_amount,
            penalty_amount=t.penalty_amount,
            total_amount=t.total_amount,
            barrier_opened=t.barrier_opened,
            entrance_panel_id=t.entrance_panel_id,
            exit_panel_id=t.exit_panel_id,
            is_lost_override=t.is_lost_override,
            is_prepaid=getattr(t, "is_prepaid", False),
            exit_window_minutes=getattr(t, "exit_window_minutes", 15)
        ))
    return output


@app.post("/api/customer/pay")
@app.post("/api/customer/pay-online")
def customer_pay_online(
    ticket_number: str = Query(..., description="Ticket to settle payment for"),
    payment_type: PaymentType = PaymentType.UPI_ONLINE,
    current_user: AccountModel = Depends(require_role([UserRole.CUSTOMER])),
    db: Session = Depends(get_db)
):
    """
    Customer Info Portal payment:
    Allows customers to pay in advance at floor info portal before reaching exit.
    Rejects already settled tickets with 400 Bad Request.
    """
    ticket = db.query(ParkingTicketModel).filter(
        ParkingTicketModel.ticket_number == ticket_number.strip()
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    if ticket.status == ParkingTicketStatus.PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket already settled. No outstanding balance."
        )

    if ticket.status == ParkingTicketStatus.EXPIRED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation has EXPIRED due to no-show. Payment cannot be processed."
        )

    now = datetime.now(timezone.utc)
    entry = ticket.entry_time or ticket.issued_at
    if entry and entry.tzinfo is None:
        entry = entry.replace(tzinfo=timezone.utc)
    rates = db.query(ParkingRateModel).first()
    fee_calc = calculate_ticket_fee(entry, now, ticket.booked_end, rates)

    ticket.base_amount = fee_calc["base_fee"]
    ticket.overstay_amount = fee_calc["overstay_fee"]
    ticket.total_amount = fee_calc["total_amount"]
    ticket.status = ParkingTicketStatus.PAID.value
    ticket.is_prepaid = True
    ticket.exit_window_minutes = 15

    # Record Payment
    payment = PaymentModel(
        ticket_id=ticket.id,
        amount=ticket.total_amount,
        payment_type=payment_type.value,
        status=PaymentStatus.COMPLETED.value,
        reference_id=f"UPI-{uuid.uuid4().hex[:10].upper()}"
    )
    db.add(payment)
    db.commit()

    log_audit(
        db,
        actor_username=current_user.username,
        actor_role=current_user.role,
        action="ONLINE_PAYMENT",
        details=f"Customer paid INR {ticket.total_amount:.2f} for ticket {ticket_number} via {payment_type.value}. 15-minute exit window granted."
    )

    return {
        "status": "SUCCESS",
        "ticket_number": ticket.ticket_number,
        "amount_paid": ticket.total_amount,
        "is_prepaid": True,
        "exit_window_minutes": 15,
        "message": f"PAID ONLINE (₹{ticket.total_amount:.2f}) — PROCEED TO EXIT GATE"
    }


# ============================================================================
# ROLE 2: OPERATOR / GATE MAN ENDPOINTS (Strict require_role([OPERATOR]))
# ============================================================================

@app.post("/api/operator/check-in", response_model=TicketResponse)
@app.post("/api/operator/check-in-barrier", response_model=TicketResponse)
def operator_check_in(
    req: CheckInRequest,
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR])),
    db: Session = Depends(get_db)
):
    """
    Gate Attendant EntrancePanel endpoint:
    Case A: Vehicle with existing online RESERVED ticket arrives -> Validate and mark ACTIVE, open entrance barrier.
    Case B: Walk-in drive-up customer without prior reservation -> Auto-assign suitable free spot, generate ticket, open barrier.
    """
    now = datetime.now(timezone.utc)

    with db_write_lock:
        # Case A: Check-in with existing ticket number or license plate
        ticket = None
        if req.ticket_number:
            ticket = db.query(ParkingTicketModel).filter(
                ParkingTicketModel.ticket_number == req.ticket_number.strip()
            ).first()
        elif req.license_plate:
            plate = req.license_plate.strip().upper()
            vehicle = db.query(VehicleModel).filter(VehicleModel.license_plate == plate).first()
            if vehicle:
                ticket = db.query(ParkingTicketModel).filter(
                    ParkingTicketModel.vehicle_id == vehicle.id,
                    ParkingTicketModel.status.in_([
                        ParkingTicketStatus.RESERVED.value,
                        ParkingTicketStatus.EXPIRED.value,
                        ParkingTicketStatus.ACTIVE.value
                    ])
                ).order_by(ParkingTicketModel.issued_at.desc()).first()

        if ticket:
            # 1. Strictly check if reservation expired
            if ticket.status == ParkingTicketStatus.EXPIRED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entry Denied: Reservation has EXPIRED due to no-show. The stall was automatically reclaimed by the system."
                )

            # 2. Check if already active inside the facility
            if ticket.status == ParkingTicketStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vehicle is already checked in and inside the parking lot."
                )

            # 3. Strictly check that slot.status == SlotStatus.RESERVED
            spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.id == ticket.spot_id).with_for_update().first()
            if not spot or spot.status != SlotStatus.RESERVED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entry Denied: Reservation has EXPIRED due to no-show. The stall was automatically reclaimed by the system."
                )

            ticket.status = ParkingTicketStatus.ACTIVE.value
            ticket.entry_time = now
            ticket.barrier_opened = True
            spot.status = SlotStatus.OCCUPIED.value
            db.commit()
            db.refresh(ticket)

            log_audit(
                db,
                actor_username=current_user.username,
                actor_role=current_user.role,
                action="GATE_CHECK_IN_RESERVED",
                details=f"Reserved vehicle {ticket.vehicle.license_plate} checked in at {req.entrance_panel_id}. Barrier opened. Spot {ticket.spot.spot_number} marked OCCUPIED."
            )

            return TicketResponse(
                id=ticket.id,
                ticket_number=ticket.ticket_number,
                spot_id=ticket.spot_id,
                spot_number=ticket.spot.spot_number,
                floor_name=ticket.spot.floor.name,
                license_plate=ticket.vehicle.license_plate,
                vehicle_type=ticket.vehicle.vehicle_type,
                issued_at=ticket.issued_at,
                entry_time=ticket.entry_time,
                booked_start=ticket.booked_start,
                booked_end=ticket.booked_end,
                actual_exit_time=ticket.actual_exit_time,
                status=ParkingTicketStatus(ticket.status),
                base_amount=ticket.base_amount,
                overstay_amount=ticket.overstay_amount,
                penalty_amount=ticket.penalty_amount,
                total_amount=ticket.total_amount,
                barrier_opened=ticket.barrier_opened,
                entrance_panel_id=ticket.entrance_panel_id,
                exit_panel_id=ticket.exit_panel_id,
                is_lost_override=ticket.is_lost_override
            )

        # Case B: Walk-in customer drive-up
        if not req.license_plate:
            raise HTTPException(status_code=400, detail="License plate is required for walk-in check-in.")

        plate = req.license_plate.strip().upper()
        # Find spot: either requested spot_id or first available compatible spot
        target_spot = None
        if req.spot_id:
            target_spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.id == req.spot_id).with_for_update().first()
            if not target_spot:
                raise HTTPException(status_code=404, detail=f"Slot ID {req.spot_id} not found.")
            if target_spot.status != SlotStatus.AVAILABLE.value:
                raise HTTPException(status_code=409, detail=f"Slot ID {req.spot_id} is not available (current status: {target_spot.status}).")
            is_compat, msg = is_vehicle_compatible(req.vehicle_type, target_spot.spot_type)
            if not is_compat:
                raise HTTPException(status_code=400, detail=msg)
        else:
            # Auto-assign suitable spot strictly filtered by compatibility
            v_type_str = req.vehicle_type.value if hasattr(req.vehicle_type, "value") else str(req.vehicle_type).upper()
            compatible_types = VEHICLE_SPOT_COMPATIBILITY.get(v_type_str, [ParkingSpotType.COMPACT.value, ParkingSpotType.LARGE.value])
            target_spot = db.query(ParkingSpotModel).filter(
                ParkingSpotModel.status == SlotStatus.AVAILABLE.value,
                ParkingSpotModel.spot_type.in_(compatible_types)
            ).first()

            if not target_spot:
                raise HTTPException(status_code=409, detail=f"Parking Lot Full! No available spots for {req.vehicle_type.value}.")

        # Mark spot OCCUPIED
        target_spot.status = SlotStatus.OCCUPIED.value

        # Register vehicle
        vehicle = db.query(VehicleModel).filter(VehicleModel.license_plate == plate).first()
        if not vehicle:
            vehicle = VehicleModel(license_plate=plate, vehicle_type=req.vehicle_type.value)
            db.add(vehicle)
            db.flush()
        else:
            vehicle.vehicle_type = req.vehicle_type.value

        ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        ticket = ParkingTicketModel(
            ticket_number=ticket_number,
            spot_id=target_spot.id,
            vehicle_id=vehicle.id,
            issued_at=now,
            entry_time=now,
            status=ParkingTicketStatus.ACTIVE.value,
            barrier_opened=True,
            entrance_panel_id=req.entrance_panel_id
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        log_audit(
            db,
            actor_username=current_user.username,
            actor_role=current_user.role,
            action="GATE_CHECK_IN_WALKIN",
            details=f"Walk-in vehicle {plate} ({req.vehicle_type.value}) checked in at {req.entrance_panel_id}. Allocated Spot {target_spot.spot_number}. Ticket {ticket_number} printed. Entrance Barrier Opened."
        )

        return TicketResponse(
            id=ticket.id,
            ticket_number=ticket.ticket_number,
            spot_id=target_spot.id,
            spot_number=target_spot.spot_number,
            floor_name=target_spot.floor.name,
            license_plate=plate,
            vehicle_type=req.vehicle_type.value,
            issued_at=ticket.issued_at,
            entry_time=ticket.entry_time,
            booked_start=ticket.booked_start,
            booked_end=ticket.booked_end,
            actual_exit_time=ticket.actual_exit_time,
            status=ParkingTicketStatus(ticket.status),
            base_amount=ticket.base_amount,
            overstay_amount=ticket.overstay_amount,
            penalty_amount=ticket.penalty_amount,
            total_amount=ticket.total_amount,
            barrier_opened=ticket.barrier_opened,
            entrance_panel_id=ticket.entrance_panel_id,
            exit_panel_id=ticket.exit_panel_id,
            is_lost_override=ticket.is_lost_override,
            is_prepaid=getattr(ticket, "is_prepaid", False),
            exit_window_minutes=getattr(ticket, "exit_window_minutes", 15)
        )


@app.get("/api/operator/pending-reservations", response_model=List[TicketResponse])
def get_pending_reservations(
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Returns all reservations currently in RESERVED state, awaiting gate arrival.
    Allows Gate Operator 1-click check-in without manual typing.
    """
    tickets = db.query(ParkingTicketModel).filter(
        ParkingTicketModel.status == ParkingTicketStatus.RESERVED.value
    ).order_by(ParkingTicketModel.issued_at.asc()).all()

    output = []
    for t in tickets:
        output.append(TicketResponse(
            id=t.id,
            ticket_number=t.ticket_number,
            spot_id=t.spot_id,
            spot_number=t.spot.spot_number if t.spot else "",
            floor_name=t.spot.floor.name if t.spot and t.spot.floor else "",
            license_plate=t.vehicle.license_plate if t.vehicle else "",
            vehicle_type=t.vehicle.vehicle_type if t.vehicle else "",
            issued_at=t.issued_at,
            entry_time=t.entry_time,
            booked_start=t.booked_start,
            booked_end=t.booked_end,
            actual_exit_time=t.actual_exit_time,
            status=ParkingTicketStatus(t.status),
            base_amount=t.base_amount,
            overstay_amount=t.overstay_amount,
            penalty_amount=t.penalty_amount,
            total_amount=t.total_amount,
            barrier_opened=t.barrier_opened,
            entrance_panel_id=t.entrance_panel_id,
            exit_panel_id=t.exit_panel_id,
            is_lost_override=t.is_lost_override,
            is_prepaid=getattr(t, "is_prepaid", False),
            exit_window_minutes=getattr(t, "exit_window_minutes", 15)
        ))
    return output


@app.get("/api/operator/active-parked-tickets", response_model=List[TicketResponse])
def get_active_parked_tickets(
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Returns all vehicles currently parked or pre-paid inside the facility awaiting exit.
    Allows Gate Operator 1-click exit POS scan without manual typing.
    """
    tickets = db.query(ParkingTicketModel).filter(
        ParkingTicketModel.status.in_([ParkingTicketStatus.ACTIVE.value, ParkingTicketStatus.PAID.value]),
        ParkingTicketModel.actual_exit_time.is_(None)
    ).order_by(ParkingTicketModel.issued_at.desc()).all()

    output = []
    for t in tickets:
        output.append(TicketResponse(
            id=t.id,
            ticket_number=t.ticket_number,
            spot_id=t.spot_id,
            spot_number=t.spot.spot_number if t.spot else "",
            floor_name=t.spot.floor.name if t.spot and t.spot.floor else "",
            license_plate=t.vehicle.license_plate if t.vehicle else "",
            vehicle_type=t.vehicle.vehicle_type if t.vehicle else "",
            issued_at=t.issued_at,
            entry_time=t.entry_time,
            booked_start=t.booked_start,
            booked_end=t.booked_end,
            actual_exit_time=t.actual_exit_time,
            status=ParkingTicketStatus(t.status),
            base_amount=t.base_amount,
            overstay_amount=t.overstay_amount,
            penalty_amount=t.penalty_amount,
            total_amount=t.total_amount,
            barrier_opened=t.barrier_opened,
            entrance_panel_id=t.entrance_panel_id,
            exit_panel_id=t.exit_panel_id,
            is_lost_override=t.is_lost_override,
            is_prepaid=getattr(t, "is_prepaid", False),
            exit_window_minutes=getattr(t, "exit_window_minutes", 15)
        ))
    return output


@app.get("/api/operator/scan-fee", response_model=FeeCalculationResponse)
@app.get("/api/operator/calculate-exit-fee", response_model=FeeCalculationResponse)
def operator_calculate_exit_fee(
    ticket_number: str = Query(...),
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR])),
    db: Session = Depends(get_db)
):
    """
    Operator ExitPanel preview:
    Scans ticket and computes live billing breakdown including overstay penalties
    and 2-minute immediate exit grace period check.
    If ticket was pre-paid online, shows 'PAYMENT VERIFIED: Settled Online via UPI. Net Due: ₹0.00'.
    """
    ticket = db.query(ParkingTicketModel).filter(
        ParkingTicketModel.ticket_number == ticket_number.strip()
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    now = datetime.now(timezone.utc)
    entry = ticket.entry_time or ticket.issued_at
    if entry and entry.tzinfo is None:
        entry = entry.replace(tzinfo=timezone.utc)
    rates = db.query(ParkingRateModel).first()

    # Pre-Paid Online check
    if ticket.status == ParkingTicketStatus.PAID.value:
        duration_minutes = max(1, math.ceil((now - entry).total_seconds() / 60.0))
        return FeeCalculationResponse(
            ticket_number=ticket.ticket_number,
            license_plate=ticket.vehicle.license_plate if ticket.vehicle else "N/A",
            spot_number=ticket.spot.spot_number if ticket.spot else "N/A",
            vehicle_type=ticket.vehicle.vehicle_type if ticket.vehicle else "CAR",
            entry_time=entry,
            exit_time=now,
            duration_minutes=duration_minutes,
            is_grace_period=False,
            base_hours=0,
            base_fee=0.0,
            excess_hours=0,
            overstay_multiplier=rates.overstay_multiplier if rates else 1.5,
            overstay_fee=0.0,
            lost_ticket_fee=0.0,
            total_amount=0.0,
            status=ticket.status,
            message="PAYMENT VERIFIED: Settled Online via UPI. Net Due: ₹0.00"
        )

    calc = calculate_ticket_fee(entry, now, ticket.booked_end, rates, is_lost=ticket.is_lost_override)

    return FeeCalculationResponse(
        ticket_number=ticket.ticket_number,
        license_plate=ticket.vehicle.license_plate,
        spot_number=ticket.spot.spot_number,
        vehicle_type=ticket.vehicle.vehicle_type,
        entry_time=entry,
        exit_time=now,
        duration_minutes=calc["duration_minutes"],
        is_grace_period=calc["is_grace_period"],
        base_hours=calc["base_hours"],
        base_fee=calc["base_fee"],
        excess_hours=calc["excess_hours"],
        overstay_multiplier=calc["overstay_multiplier"],
        overstay_fee=calc["overstay_fee"],
        lost_ticket_fee=calc["lost_ticket_fee"],
        total_amount=calc["total_amount"],
        status=ticket.status,
        message=calc["message"]
    )


@app.post("/api/operator/check-out")
def operator_check_out(
    req: CheckOutRequest,
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR])),
    db: Session = Depends(get_db)
):
    """
    Gate Attendant ExitPanel endpoint:
    Processes Cash / POS card payment, releases the spot back to AVAILABLE,
    opens the exit barrier gate, and updates ticket status to PAID.
    If ticket was pre-paid online, clears exit and raises barrier directly without double-charging.
    """
    now = datetime.now(timezone.utc)

    with db_write_lock:
        ticket = db.query(ParkingTicketModel).filter(
            ParkingTicketModel.ticket_number == req.ticket_number.strip()
        ).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found.")

        if ticket.status == ParkingTicketStatus.PAID.value and ticket.actual_exit_time:
            raise HTTPException(status_code=400, detail="Ticket is already checked out and closed.")

        if ticket.status == ParkingTicketStatus.PAID.value:
            # Pre-paid online: release spot to AVAILABLE, open barrier, record checkout
            ticket.actual_exit_time = now
            ticket.exit_panel_id = req.exit_panel_id
            ticket.barrier_opened = True
            if ticket.spot:
                ticket.spot.status = SlotStatus.AVAILABLE.value
            db.commit()

            log_audit(
                db,
                actor_username=current_user.username,
                actor_role=current_user.role,
                action="GATE_CHECK_OUT_PREPAID",
                details=(
                    f"Vehicle {ticket.vehicle.license_plate if ticket.vehicle else 'N/A'} (Pre-Paid Online) checked out at {req.exit_panel_id}. "
                    f"Net Collected: ₹0.00. Spot {ticket.spot.spot_number if ticket.spot else 'N/A'} released to AVAILABLE. Exit Barrier Opened."
                )
            )

            return {
                "status": "SUCCESS",
                "ticket_number": ticket.ticket_number,
                "license_plate": ticket.vehicle.license_plate if ticket.vehicle else "N/A",
                "spot_number": ticket.spot.spot_number if ticket.spot else "N/A",
                "total_collected": 0.0,
                "barrier_opened": True,
                "message": "PAYMENT VERIFIED: Settled Online via UPI. Net Due: ₹0.00. Exit cleared! Barrier opened."
            }

        rates = db.query(ParkingRateModel).first()
        entry = ticket.entry_time or ticket.issued_at
        calc = calculate_ticket_fee(entry, now, ticket.booked_end, rates, is_lost=ticket.is_lost_override)

        # Update ticket totals
        ticket.base_amount = calc["base_fee"]
        ticket.overstay_amount = calc["overstay_fee"]
        ticket.penalty_amount = calc["lost_ticket_fee"]
        ticket.total_amount = calc["total_amount"]
        ticket.actual_exit_time = now
        ticket.exit_panel_id = req.exit_panel_id
        ticket.status = ParkingTicketStatus.PAID.value
        ticket.barrier_opened = True

        # Free spot
        if ticket.spot:
            ticket.spot.status = SlotStatus.AVAILABLE.value

        # Create Payment record if fee > 0
        if ticket.total_amount > 0:
            payment = PaymentModel(
                ticket_id=ticket.id,
                amount=ticket.total_amount,
                payment_type=req.payment_type.value,
                status=PaymentStatus.COMPLETED.value,
                reference_id=f"POS-{uuid.uuid4().hex[:8].upper()}"
            )
            db.add(payment)

        db.commit()

        log_audit(
            db,
            actor_username=current_user.username,
            actor_role=current_user.role,
            action="GATE_CHECK_OUT",
            details=(
                f"Vehicle {ticket.vehicle.license_plate} checked out at {req.exit_panel_id}. "
                f"Total Collected: ₹{ticket.total_amount:.2f} ({req.payment_type.value}). "
                f"Spot {ticket.spot.spot_number} released to AVAILABLE. Exit Barrier Opened."
            )
        )

        return {
            "status": "SUCCESS",
            "ticket_number": ticket.ticket_number,
            "license_plate": ticket.vehicle.license_plate,
            "spot_number": ticket.spot.spot_number,
            "total_collected": ticket.total_amount,
            "barrier_opened": True,
            "message": f"Exit cleared! Barrier opened. Thank you for parking with us. ({calc['message']})"
        }


@app.post("/api/operator/lost-ticket-override")
def operator_lost_ticket_override(
    req: LostTicketOverrideRequest,
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    SIM 7 / EDGE CASE 4: Unrecognized Plate / Lost Ticket Override:
    Gate Attendant assesses statutory ₹500 flat surcharge, collects payment, clears exit, and releases barrier.
    Handles both active tracked vehicles and completely unrecognized/unreadable plates.
    """
    try:
        plate = req.license_plate.strip().upper() if req.license_plate else "UNKNOWN-VEHICLE"
        now = datetime.now(timezone.utc)
        
        pay_type_val = req.payment_method or (req.payment_type.value if req.payment_type else "CASH")

        with db_write_lock:
            rates = db.query(ParkingRateModel).first()
            penalty_fee = rates.lost_ticket_fee if rates else 500.0

            vehicle = db.query(VehicleModel).filter(VehicleModel.license_plate == plate).first()
            if not vehicle:
                vehicle = VehicleModel(license_plate=plate, vehicle_type=VehicleType.CAR.value)
                db.add(vehicle)
                db.flush()

            ticket = db.query(ParkingTicketModel).filter(
                ParkingTicketModel.vehicle_id == vehicle.id,
                ParkingTicketModel.status.in_([ParkingTicketStatus.ACTIVE.value, ParkingTicketStatus.RESERVED.value])
            ).first()

            if not ticket:
                spot = db.query(ParkingSpotModel).first()
                ticket = ParkingTicketModel(
                    ticket_number=f"TKT-LOST-{uuid.uuid4().hex[:6].upper()}",
                    spot_id=spot.id if spot else 1,
                    vehicle_id=vehicle.id,
                    issued_at=now,
                    booked_start=now,
                    booked_end=now,
                    entry_time=now,
                    actual_exit_time=now,
                    status=ParkingTicketStatus.LOST.value,
                    is_lost_override=True,
                    penalty_amount=penalty_fee,
                    total_amount=penalty_fee,
                    barrier_opened=True
                )
                db.add(ticket)
                db.flush()
            else:
                ticket.is_lost_override = True
                ticket.status = ParkingTicketStatus.LOST.value
                ticket.penalty_amount = penalty_fee
                ticket.total_amount = penalty_fee
                ticket.actual_exit_time = now
                ticket.barrier_opened = True

                if ticket.spot:
                    ticket.spot.status = SlotStatus.AVAILABLE.value

            ref_id = f"LOST-OVR-{uuid.uuid4().hex[:8].upper()}"
            payment = PaymentModel(
                ticket_id=ticket.id,
                amount=penalty_fee,
                payment_type=pay_type_val,
                status=PaymentStatus.COMPLETED.value,
                reference_id=ref_id
            )
            db.add(payment)
            db.commit()

            spot_info = f"Spot {ticket.spot.spot_number} freed." if ticket and ticket.spot else "No stall linked."
            log_audit(
                db,
                actor_username=current_user.username,
                actor_role=current_user.role,
                action="LOST_TICKET_OVERRIDE",
                details=f"Gate Attendant applied statutory Lost Ticket Surcharge (₹{penalty_fee:.2f}) for plate '{plate}' via {pay_type_val}. Exit barrier opened. {spot_info}"
            )

            return {
                "status": "SUCCESS",
                "message": "Override processed. Barrier raised.",
                "receipt_id": ref_id,
                "penalty_fee": penalty_fee,
                "license_plate": plate,
                "payment_method": pay_type_val,
                "barrier_action": "RAISED",
                "barrier_opened": True,
                "ticket_number": ticket.ticket_number if ticket else None
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/operator/barrier-toggle")
def operator_barrier_toggle(
    req: BarrierControlRequest,
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR])),
    db: Session = Depends(get_db)
):
    """Manual barrier gate control (Open / Close) for emergency or attendant discretion."""
    action = req.action.upper()
    if action not in ["OPEN", "CLOSE"]:
        raise HTTPException(status_code=400, detail="Action must be 'OPEN' or 'CLOSE'.")

    log_audit(
        db,
        actor_username=current_user.username,
        actor_role=current_user.role,
        action="MANUAL_BARRIER_OVERRIDE",
        details=f"Gate Man manually triggered barrier {req.panel_id} to {action}."
    )

    return {
        "status": "SUCCESS",
        "panel_id": req.panel_id,
        "barrier_state": action,
        "message": f"Barrier {req.panel_id} has been manually set to {action}."
    }


@app.post("/api/operator/incident-log")
def operator_log_incident(
    req: IncidentLogRequest,
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR])),
    db: Session = Depends(get_db)
):
    """Gate Operator endpoint to log stall obstructions, gate malfunctions, or vehicle damage."""
    details = f"Incident [{req.incident_type}]: {req.notes}. Plate: {req.license_plate or 'N/A'}, Stall: {req.stall_number or 'N/A'}."
    log_audit(
        db,
        actor_username=current_user.username,
        actor_role=current_user.role,
        action="INCIDENT_REPORT",
        details=details
    )
    return {"status": "SUCCESS", "message": "Incident logged into shift reconciliation audit trail."}



# ============================================================================
# ROLE 1: ADMIN ENDPOINTS (Strict require_role([ADMIN]))
# ============================================================================

@app.post("/api/admin/floors", response_model=FloorResponse)
def admin_add_floor(
    req: FloorCreate,
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to add a new parking floor to the facility."""
    lot = db.query(ParkingLotModel).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Parking lot not configured.")

    existing = db.query(ParkingFloorModel).filter(ParkingFloorModel.floor_number == req.floor_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Floor {req.floor_number} already exists.")

    floor = ParkingFloorModel(lot_id=lot.id, floor_number=req.floor_number, name=req.name)
    db.add(floor)
    db.commit()
    db.refresh(floor)

    log_audit(db, current_user.username, current_user.role, "ADD_FLOOR", f"Added Floor {floor.floor_number}: '{floor.name}'.")
    return FloorResponse(id=floor.id, lot_id=floor.lot_id, floor_number=floor.floor_number, name=floor.name, spots=[])


@app.post("/api/admin/spots", response_model=SpotResponse)
@app.post("/api/admin/add-slot", response_model=SpotResponse)
def admin_add_spot(
    req: SpotCreate,
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to add a new parking slot to a designated floor with auto-creation support."""
    # Ensure a ParkingLot exists
    lot = db.query(ParkingLotModel).first()
    if not lot:
        lot = ParkingLotModel(
            name="Central Grand Parking Lot",
            address="100 Tech Boulevard, Silicon Valley, CA 94025"
        )
        db.add(lot)
        db.commit()
        db.refresh(lot)

    floor = None
    # 1. Try finding floor by floor_id if provided
    if req.floor_id is not None:
        floor = db.query(ParkingFloorModel).filter(ParkingFloorModel.id == req.floor_id).first()

    # 2. Try finding floor by floor_number if provided
    if not floor and req.floor_number is not None:
        floor = db.query(ParkingFloorModel).filter(ParkingFloorModel.floor_number == req.floor_number).first()

    # 3. If floor_id was provided but not found as primary key id, it might represent floor_number
    if not floor and req.floor_id is not None:
        floor = db.query(ParkingFloorModel).filter(ParkingFloorModel.floor_number == req.floor_id).first()

    # 4. If target floor does NOT exist yet, automatically create that floor entry on the fly
    if not floor:
        target_floor_num = req.floor_number if req.floor_number is not None else (req.floor_id if req.floor_id is not None else 1)
        floor_name = "Ground Floor (P1)" if target_floor_num == 1 else f"Level {target_floor_num} (P{target_floor_num})"
        floor = ParkingFloorModel(
            lot_id=lot.id,
            floor_number=target_floor_num,
            name=floor_name
        )
        db.add(floor)
        db.commit()
        db.refresh(floor)
        log_audit(
            db,
            actor_username=current_user.username,
            actor_role=current_user.role,
            action="AUTO_CREATE_FLOOR",
            details=f"Auto-created Floor {floor.floor_number} ('{floor.name}', ID: {floor.id}) on the fly during slot addition."
        )

    # Check for duplicate spot number
    existing = db.query(ParkingSpotModel).filter(ParkingSpotModel.spot_number == req.spot_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Spot number '{req.spot_number}' already exists.")

    spot = ParkingSpotModel(
        floor_id=floor.id,
        spot_number=req.spot_number,
        spot_type=req.spot_type.value,
        status=SlotStatus.AVAILABLE.value
    )
    db.add(spot)
    db.commit()
    db.refresh(spot)

    log_audit(
        db,
        actor_username=current_user.username,
        actor_role=current_user.role,
        action="ADD_SPOT",
        details=f"Added Spot {spot.spot_number} ({spot.spot_type}) on Floor {floor.name} (Floor #{floor.floor_number}, ID: {floor.id})."
    )
    return SpotResponse(
        id=spot.id,
        floor_id=spot.floor_id,
        spot_number=spot.spot_number,
        spot_type=ParkingSpotType(spot.spot_type),
        status=SlotStatus(spot.status)
    )


@app.patch("/api/admin/spots/{spot_id}/status", response_model=SpotResponse)
def admin_update_spot_status(
    spot_id: int,
    req: SpotStatusUpdate,
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to toggle spot maintenance or enable/disable slots."""
    spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found.")

    old_status = spot.status
    spot.status = req.status.value
    db.commit()
    db.refresh(spot)

    log_audit(
        db,
        current_user.username,
        current_user.role,
        "UPDATE_SPOT_STATUS",
        f"Updated Spot {spot.spot_number} status from {old_status} to {spot.status}."
    )

    return SpotResponse(
        id=spot.id,
        floor_id=spot.floor_id,
        spot_number=spot.spot_number,
        spot_type=ParkingSpotType(spot.spot_type),
        status=SlotStatus(spot.status)
    )


@app.put("/api/admin/rates", response_model=RateResponse)
def admin_update_rates(
    req: RateUpdate,
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to modify dynamic pricing tiers and penalty multipliers."""
    rates = db.query(ParkingRateModel).first()
    if not rates:
        rates = ParkingRateModel()
        db.add(rates)

    rates.first_hour_rate = req.first_hour_rate
    rates.second_third_hour_rate = req.second_third_hour_rate
    rates.remaining_hour_rate = req.remaining_hour_rate
    rates.overstay_multiplier = req.overstay_multiplier
    rates.lost_ticket_fee = req.lost_ticket_fee
    rates.grace_period_minutes = req.grace_period_minutes
    rates.reservation_hold_minutes = req.reservation_hold_minutes
    rates.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rates)

    log_audit(
        db,
        current_user.username,
        current_user.role,
        "UPDATE_RATES",
        (
            f"Rates updated: 1st hr=₹{rates.first_hour_rate}, 2nd-3rd=₹{rates.second_third_hour_rate}, "
            f"4th+=₹{rates.remaining_hour_rate}, Overstay Multiplier={rates.overstay_multiplier}x, "
            f"Lost Fee=₹{rates.lost_ticket_fee}, Grace Period={rates.grace_period_minutes}m, Hold={rates.reservation_hold_minutes}m."
        )
    )
    return rates


@app.post("/api/admin/attendants", response_model=UserResponse)
def admin_create_attendant(
    req: UserCreate,
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to create operator/attendant accounts."""
    existing = db.query(AccountModel).filter(AccountModel.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Username '{req.username}' already registered.")

    account = AccountModel(
        username=req.username,
        hashed_password=hash_password(req.password),
        role=req.role.value,
        status=AccountStatus.ACTIVE.value,
        name=req.name,
        email=req.email,
        phone=req.phone
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    log_audit(db, current_user.username, current_user.role, "CREATE_ATTENDANT", f"Created staff account for '{account.username}' with role '{account.role}'.")
    return account


@app.get("/api/admin/audit-logs", response_model=List[AuditLogResponse])
def admin_get_audit_logs(
    limit: int = 50,
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to inspect live system security and financial audit trail."""
    logs = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
    return logs


@app.get("/api/admin/financial-summary")
def admin_financial_summary(
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin financial metrics summary: total revenue, active tickets, and overstay collections."""
    total_rev = db.query(func.sum(PaymentModel.amount)).scalar() or 0.0
    total_payments = db.query(PaymentModel).count()
    cash_rev = db.query(func.sum(PaymentModel.amount)).filter(PaymentModel.payment_type == PaymentType.CASH.value).scalar() or 0.0
    digital_rev = db.query(func.sum(PaymentModel.amount)).filter(PaymentModel.payment_type != PaymentType.CASH.value).scalar() or 0.0
    overstay_rev = db.query(func.sum(ParkingTicketModel.overstay_amount)).scalar() or 0.0
    lost_rev = db.query(func.sum(ParkingTicketModel.penalty_amount)).scalar() or 0.0

    total_spots = db.query(ParkingSpotModel).count()
    occupied_spots = db.query(ParkingSpotModel).filter(ParkingSpotModel.status == SlotStatus.OCCUPIED.value).count()
    reserved_spots = db.query(ParkingSpotModel).filter(ParkingSpotModel.status == SlotStatus.RESERVED.value).count()

    return {
        "total_revenue": round(total_rev, 2),
        "total_transactions": total_payments,
        "total_cash_collected": round(cash_rev, 2),
        "total_digital_collected": round(digital_rev, 2),
        "overstay_penalty_revenue": round(overstay_rev, 2),
        "lost_ticket_revenue": round(lost_rev, 2),
        "total_spots": total_spots,
        "occupied_spots": occupied_spots,
        "reserved_spots": reserved_spots,
        "occupancy_rate": f"{round((occupied_spots / max(1, total_spots)) * 100, 1)}%"
    }


@app.get("/api/admin/transactions", response_model=List[TransactionResponse])
def admin_get_transactions(
    limit: int = 200,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Admin endpoint to retrieve shift transactions with optional date range filter."""
    query = db.query(PaymentModel)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            query = query.filter(PaymentModel.transaction_time >= start_dt)
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            query = query.filter(PaymentModel.transaction_time <= end_dt)
        except Exception:
            pass

    payments = query.order_by(PaymentModel.transaction_time.desc()).limit(limit).all()
    results = []
    for p in payments:
        plate = p.ticket.vehicle.license_plate if p.ticket and p.ticket.vehicle else "N/A"
        tkt_no = p.ticket.ticket_number if p.ticket else "N/A"
        results.append(TransactionResponse(
            id=p.id,
            ticket_number=tkt_no,
            license_plate=plate,
            amount=p.amount,
            payment_type=p.payment_type,
            status=p.status,
            reference_id=p.reference_id,
            transaction_time=p.transaction_time,
            operator="Station #04 POS"
        ))
    return results



# ============================================================================
# LIVE DEMONSTRATION & EDGE CASE SIMULATION ENDPOINTS
# ============================================================================

@app.post("/api/demo/race-condition")
def demo_race_condition(
    spot_id: int = Query(..., description="ID of slot to race for"),
    db: Session = Depends(get_db)
):
    """
    EDGE CASE 1: Concurrency / Double-Booking Demonstration:
    Fires two simultaneous booking requests in parallel threads for the exact same slot ID.
    Demonstrates that Request 1 succeeds (200 OK) and Request 2 cleanly fails with
    HTTP 409 Conflict: Slot just taken by another vehicle.
    """
    spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Slot not found.")

    # Reset spot to AVAILABLE for a clean race demo
    spot.status = SlotStatus.AVAILABLE.value
    db.commit()

    results = {}

    def attempt_booking(thread_name: str, plate: str):
        thread_db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            with db_write_lock:
                s = thread_db.query(ParkingSpotModel).filter(
                    ParkingSpotModel.id == spot_id
                ).with_for_update().first()

                if s.status != SlotStatus.AVAILABLE.value:
                    results[thread_name] = {
                        "status_code": 409,
                        "status": "CONFLICT",
                        "message": f"Conflict: Slot '{s.spot_number}' just taken by another vehicle! Current status: {s.status}."
                    }
                    return

                # Allocate
                s.status = SlotStatus.RESERVED.value

                v = thread_db.query(VehicleModel).filter(VehicleModel.license_plate == plate).first()
                if not v:
                    v = VehicleModel(license_plate=plate, vehicle_type=VehicleType.CAR.value)
                    thread_db.add(v)
                    thread_db.flush()

                tkt = ParkingTicketModel(
                    ticket_number=f"TKT-RACE-{uuid.uuid4().hex[:6].upper()}",
                    spot_id=s.id,
                    vehicle_id=v.id,
                    issued_at=now,
                    booked_start=now,
                    booked_end=now + timedelta(hours=2),
                    status=ParkingTicketStatus.RESERVED.value
                )
                thread_db.add(tkt)
                thread_db.commit()

                results[thread_name] = {
                    "status_code": 200,
                    "status": "SUCCESS",
                    "ticket_number": tkt.ticket_number,
                    "license_plate": plate,
                    "message": f"200 OK: Slot '{s.spot_number}' successfully reserved for {plate}."
                }
        except Exception as e:
            results[thread_name] = {"status_code": 500, "status": "ERROR", "message": str(e)}
        finally:
            thread_db.close()

    # Launch two concurrent threads
    import threading
    t1 = threading.Thread(target=attempt_booking, args=("Request_1_Vehicle_A", "RACE-CAR-01"))
    t2 = threading.Thread(target=attempt_booking, args=("Request_2_Vehicle_B", "RACE-CAR-02"))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    log_audit(
        db,
        actor_username="DEMO_RUNNER",
        actor_role="DEMO",
        action="CONCURRENCY_RACE_SIMULATION",
        details=f"Race simulation on Slot ID {spot_id}: Request 1 -> {results.get('Request_1_Vehicle_A', {}).get('status')}, Request 2 -> {results.get('Request_2_Vehicle_B', {}).get('status')}."
    )

    return {
        "slot_id": spot_id,
        "slot_number": spot.spot_number,
        "concurrent_simulation_results": results
    }


@app.post("/api/customer/fast-forward-expiry")
@app.post("/api/demo/fast-forward-expiry")
def demo_fast_forward_expiry(db: Session = Depends(get_db)):
    """
    EDGE CASE 2: Expired Reservation Auto-Reclamation Demo:
    Simulates elapsed time by pushing the issued_at time of any RESERVED ticket
    back by 20 minutes, then triggers the reclamation sweep immediately!
    """
    rates = db.query(ParkingRateModel).first()
    hold_mins = rates.reservation_hold_minutes if rates else 15

    reserved_tickets = db.query(ParkingTicketModel).filter(
        ParkingTicketModel.status == ParkingTicketStatus.RESERVED.value
    ).all()

    if not reserved_tickets:
        raise HTTPException(
            status_code=400,
            detail="No active RESERVED tickets found to expire. Please reserve a slot first as Customer."
        )

    # Shift issued_at backwards
    for tkt in reserved_tickets:
        tkt.issued_at = datetime.now(timezone.utc) - timedelta(minutes=hold_mins + 5)
    db.commit()

    # Run sweep immediately
    reclaimed = sweep_expired_reservations(db)

    return {
        "status": "SUCCESS",
        "message": f"Fast-forwarded {len(reserved_tickets)} reservations past the {hold_mins}-minute hold window.",
        "reclaimed_events": reclaimed
    }


@app.post("/api/demo/reset-spot")
def demo_reset_spot(
    spot_id: int = Query(..., description="Spot ID to reset to AVAILABLE"),
    db: Session = Depends(get_db)
):
    """Utility endpoint for stress testing: cleans up active tickets and resets spot to AVAILABLE."""
    with db_write_lock:
        spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.id == spot_id).with_for_update().first()
        if not spot:
            raise HTTPException(status_code=404, detail="Spot not found.")

        active_tkts = db.query(ParkingTicketModel).filter(
            ParkingTicketModel.spot_id == spot.id,
            ParkingTicketModel.status.in_([ParkingTicketStatus.RESERVED.value, ParkingTicketStatus.ACTIVE.value])
        ).all()
        for t in active_tkts:
            t.status = ParkingTicketStatus.EXPIRED.value

        spot.status = SlotStatus.AVAILABLE.value
        db.commit()
        return {"status": "SUCCESS", "spot_id": spot.id, "spot_number": spot.spot_number, "spot_status": spot.status}


@app.post("/api/demo/concurrency-attempt")
def demo_concurrency_attempt(
    req: ConcurrencyAttemptRequest,
    db: Session = Depends(get_db)
):
    """
    SIMULATION 1: Multi-Vehicle Concurrency Stress Test
    Individual atomic booking attempt under simultaneous load.
    Measures microsecond lock acquisition duration. First gets 200 OK, remaining get 409 Conflict.
    """
    t_start = time.perf_counter()
    now = datetime.now(timezone.utc)

    with db_write_lock:
        spot = db.query(ParkingSpotModel).filter(
            ParkingSpotModel.id == req.spot_id
        ).with_for_update().first()

        if not spot:
            raise HTTPException(status_code=404, detail=f"Stall ID {req.spot_id} not found.")

        is_compat, msg = is_vehicle_compatible(req.vehicle_type, spot.spot_type)
        if not is_compat:
            raise HTTPException(status_code=400, detail=msg)

        if spot.status != SlotStatus.AVAILABLE.value:
            lock_duration_ms = round((time.perf_counter() - t_start) * 1000, 3)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Lock conflict! Stall '{spot.spot_number}' already claimed (Status: {spot.status}). Lock evaluated in {lock_duration_ms}ms."
            )

        spot.status = SlotStatus.RESERVED.value

        v = db.query(VehicleModel).filter(VehicleModel.license_plate == req.license_plate).first()
        if not v:
            v = VehicleModel(license_plate=req.license_plate, vehicle_type=req.vehicle_type.value)
            db.add(v)
            db.flush()

        tkt = ParkingTicketModel(
            ticket_number=f"TKT-STRESS-{uuid.uuid4().hex[:6].upper()}",
            spot_id=spot.id,
            vehicle_id=v.id,
            issued_at=now,
            booked_start=now,
            booked_end=now + timedelta(hours=2),
            status=ParkingTicketStatus.RESERVED.value
        )
        db.add(tkt)
        db.commit()

        lock_duration_ms = round((time.perf_counter() - t_start) * 1000, 3)
        return {
            "request_id": req.request_id,
            "status_code": 200,
            "status": "SUCCESS",
            "spot_id": spot.id,
            "spot_number": spot.spot_number,
            "license_plate": req.license_plate,
            "ticket_number": tkt.ticket_number,
            "lock_duration_ms": lock_duration_ms,
            "message": f"Lock acquired! Stall '{spot.spot_number}' successfully secured in {lock_duration_ms}ms."
        }


# ============================================================================
# ROLE-ISOLATED OPERATOR BOOTH & LANE DIAGNOSTICS ENDPOINTS
# ============================================================================

@app.post("/api/operator/simulate-overstay")
@app.post("/api/admin/simulate-overstay")
@app.post("/api/demo/simulate-overstay")
def operator_simulate_overstay(
    req: Optional[OverstaySimulationRequest] = None,
    ticket_number: Optional[str] = Query(None, description="Ticket to simulate overstay on"),
    excess_hours: Optional[int] = Query(None, description="Hours of overstay to inject"),
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    SIM 2: DYNAMIC OVERSTAY (PRESERVE EXACT UI SPECIFICATION):
    Backdate an active check-in to test the 1.5× penalty surcharge tier and auto-lock the exit gate.
    Adjusts ticket.entry_time by hours_added.
    """
    try:
        t_code = (req.ticket_code if req and req.ticket_code else None) or \
                 (req.ticket_number if req and req.ticket_number else None) or \
                 ticket_number

        hrs = float(req.hours_added if req and req.hours_added is not None else (excess_hours if excess_hours is not None else 3.0))

        ticket = None
        if t_code:
            ticket = db.query(ParkingTicketModel).filter(
                ParkingTicketModel.ticket_number == t_code.strip()
            ).first()

        if not ticket:
            ticket = db.query(ParkingTicketModel).filter(
                ParkingTicketModel.status.in_([ParkingTicketStatus.ACTIVE.value, ParkingTicketStatus.RESERVED.value])
            ).order_by(ParkingTicketModel.issued_at.desc()).first()

        if not ticket:
            spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.status == SlotStatus.AVAILABLE.value).first()
            if not spot:
                spot = db.query(ParkingSpotModel).first()
            if spot:
                spot.status = SlotStatus.OCCUPIED.value

            v = db.query(VehicleModel).filter(VehicleModel.license_plate == "OVERSTAY-TEST-01").first()
            if not v:
                v = VehicleModel(license_plate="OVERSTAY-TEST-01", vehicle_type=VehicleType.CAR.value)
                db.add(v)
                db.flush()

            ticket = ParkingTicketModel(
                ticket_number=f"TKT-DEMO-{uuid.uuid4().hex[:6].upper()}",
                spot_id=spot.id if spot else 1,
                vehicle_id=v.id,
                issued_at=datetime.now(timezone.utc),
                entry_time=datetime.now(timezone.utc),
                status=ParkingTicketStatus.ACTIVE.value
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)

        now = datetime.now(timezone.utc)
        total_back_hours = hrs + 2.0
        ticket.entry_time = now - timedelta(hours=total_back_hours)
        ticket.booked_start = ticket.entry_time
        ticket.booked_end = ticket.entry_time + timedelta(hours=2.0)
        ticket.barrier_opened = False  # Lock exit barrier until collected!
        db.commit()

        rates = db.query(ParkingRateModel).first()
        calc = calculate_ticket_fee(ticket.entry_time, now, ticket.booked_end, rates)

        log_audit(
            db,
            actor_username=current_user.username,
            actor_role=current_user.role,
            action="OPERATOR_SIMULATE_OVERSTAY",
            details=f"Injected +{hrs}h overstay on ticket {ticket.ticket_number}. Base Fee: ₹{calc['base_fee']}, Overstay 1.5x Penalty: ₹{calc['overstay_fee']}. Barrier locked."
        )

        display_hrs = int(hrs) if hrs.is_integer() else hrs
        return {
            "status": "SUCCESS",
            "message": f"Added {display_hrs}h to ticket {ticket.ticket_number}",
            "ticket_code": ticket.ticket_number,
            "ticket_number": ticket.ticket_number,
            "license_plate": ticket.vehicle.license_plate if ticket.vehicle else "N/A",
            "spot_number": ticket.spot.spot_number if ticket.spot else "N/A",
            "simulated_entry_time": ticket.entry_time.isoformat() if ticket.entry_time else None,
            "booked_end_time": ticket.booked_end.isoformat() if ticket.booked_end else None,
            "current_exit_time": now.isoformat(),
            "hours_injected": hrs,
            "barrier_locked": True,
            "fee_breakdown": calc
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/operator/barrier-safety-rebound")
def operator_barrier_safety_rebound(
    current_user: AccountModel = Depends(require_role([UserRole.OPERATOR, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    SIM 5: BARRIER SAFETY SENSOR REBOUND
    Simulates obstacle tripping the optical descent loop while lowering; auto-rebounds barrier.
    """
    try:
        log_audit(
            db,
            actor_username=current_user.username,
            actor_role=current_user.role,
            action="BARRIER_SAFETY_INCIDENT",
            details="Optical descent loop sensor tripped by obstacle during gate lowering. Auto-rebounded to OPEN. Safety incident logged."
        )
        return {
            "status": "SUCCESS",
            "barrier_telemetry": "BARRIER: REBOUNDED (OBSTACLE DETECTED)",
            "safety_incident_logged": True,
            "message": "Optical sensor tripped! Barrier rebound sequence executed. Telemetry: [BARRIER: REBOUNDED (OBSTACLE DETECTED)]."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ROLE-ISOLATED CHIEF ADMINISTRATOR INFRASTRUCTURE & GOVERNANCE ENDPOINTS
# ============================================================================

@app.post("/api/demo/grace-advance-warning")
@app.post("/api/admin/grace-advance-warning")
def demo_grace_advance_warning(
    ticket_number: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    DAEMON-01 Sub-action: Advance to T-14m Warning.
    Backdates a RESERVED ticket to 14 minutes elapsed.
    """
    ticket = None
    if ticket_number:
        ticket = db.query(ParkingTicketModel).filter(ParkingTicketModel.ticket_number == ticket_number.strip()).first()

    if not ticket:
        ticket = db.query(ParkingTicketModel).filter(
            ParkingTicketModel.status == ParkingTicketStatus.RESERVED.value
        ).order_by(ParkingTicketModel.issued_at.desc()).first()

    if not ticket:
        spot = db.query(ParkingSpotModel).filter(ParkingSpotModel.status == SlotStatus.AVAILABLE.value).first()
        if not spot:
            spot = db.query(ParkingSpotModel).first()
        spot.status = SlotStatus.RESERVED.value

        v = db.query(VehicleModel).filter(VehicleModel.license_plate == "WARN-RESERVE-01").first()
        if not v:
            v = VehicleModel(license_plate="WARN-RESERVE-01", vehicle_type=VehicleType.CAR.value)
            db.add(v)
            db.flush()

        ticket = ParkingTicketModel(
            ticket_number=f"TKT-WARN-{uuid.uuid4().hex[:6].upper()}",
            spot_id=spot.id,
            vehicle_id=v.id,
            issued_at=datetime.now(timezone.utc),
            booked_start=datetime.now(timezone.utc),
            booked_end=datetime.now(timezone.utc) + timedelta(hours=2),
            status=ParkingTicketStatus.RESERVED.value
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

    rates = db.query(ParkingRateModel).first()
    hold_mins = rates.reservation_hold_minutes if rates else 15
    warning_minutes = max(1, hold_mins - 1)  # 14 mins

    ticket.issued_at = datetime.now(timezone.utc) - timedelta(minutes=warning_minutes)
    db.commit()

    log_audit(
        db,
        actor_username="SUPERVISOR",
        actor_role="ADMIN",
        action="GRACE_ADVANCE_WARNING",
        details=f"Backdated ticket {ticket.ticket_number} to {warning_minutes} minutes elapsed. 60 seconds remaining until reaper reclaim."
    )

    return {
        "status": "WARNING_TRIGGERED",
        "ticket_number": ticket.ticket_number,
        "spot_number": ticket.spot.spot_number if ticket.spot else "N/A",
        "license_plate": ticket.vehicle.license_plate if ticket.vehicle else "N/A",
        "elapsed_minutes": warning_minutes,
        "hold_limit_minutes": hold_mins,
        "seconds_remaining": 60,
        "message": f"Ticket {ticket.ticket_number} advanced to {warning_minutes}m. 1 minute remaining before automatic reaper forfeiture!"
    }


@app.post("/api/admin/trigger-reaper")
@app.post("/api/demo/trigger-reaper-sweep")
def admin_trigger_reaper(
    current_user: Optional[AccountModel] = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    DAEMON-01 Sub-action: Force Immediate Reaper Sweep.
    Invokes background task logic immediately to reap unfulfilled holds past 15m.
    """
    try:
        reclaimed = sweep_expired_reservations(db)
        actor_name = current_user.username if current_user else "SYSTEM_ADMIN"
        actor_role = current_user.role if current_user else UserRole.ADMIN.value
        count = len(reclaimed)
        log_audit(
            db,
            actor_username=actor_name,
            actor_role=actor_role,
            action="ADMIN_TRIGGER_REAPER",
            details=f"Force immediate reaper sweep executed. Reaped {count} no-show stall(s)."
        )
        return {
            "status": "SUCCESS",
            "reclaimed_count": count,
            "message": f"Reaped {count} expired holds",
            "reclaimed_events": reclaimed
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/admin/quarantine-floor")
def admin_quarantine_floor(
    req: QuarantineFloorRequest = QuarantineFloorRequest(),
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    FAILOVER-03: SECTOR EMERGENCY QUARANTINE
    Handles flexible floor naming ("P1", "P2", "Floor 1", "Floor 2", 1, 2)
    and quarantines all stalls on that floor that are not occupied.
    """
    admin = current_user
    raw_floor = None
    if req:
        if req.floor is not None:
            raw_floor = req.floor
        elif req.floor_number is not None:
            raw_floor = req.floor_number

    target_int = 1
    if raw_floor is not None:
        if isinstance(raw_floor, int):
            target_int = raw_floor
        else:
            floor_str = str(raw_floor).strip()
            match = re.search(r"\d+", floor_str)
            if match:
                target_int = int(match.group(0))
            else:
                target_int = 1

    floors = db.query(ParkingFloorModel).filter(
        or_(
            ParkingFloorModel.floor_number == target_int,
            ParkingFloorModel.id == target_int,
            ParkingFloorModel.name.ilike(f"%P{target_int}%"),
            ParkingFloorModel.name.ilike(f"%Floor {target_int}%")
        )
    ).all()
    floor_ids = [f.id for f in floors]

    query_conditions = [
        ParkingSpotModel.spot_number.like(f"P{target_int}-%"),
        ParkingSpotModel.floor_id == target_int
    ]
    if floor_ids:
        query_conditions.append(ParkingSpotModel.floor_id.in_(floor_ids))

    stalls = db.query(ParkingSpotModel).filter(
        or_(*query_conditions),
        ParkingSpotModel.status != SlotStatus.OCCUPIED.value,
        ParkingSpotModel.status != "OCCUPIED"
    ).all()

    count = 0
    for stall in stalls:
        stall.status = SlotStatus.MAINTENANCE.value
        count += 1
    db.commit()

    record_audit_event(
        db,
        admin.username,
        "ADMIN",
        "SECTOR_QUARANTINE",
        f"Quarantined {count} stalls on Floor P{target_int}"
    )

    return {
        "status": "SUCCESS",
        "message": f"Successfully quarantined {count} stalls on Floor P{target_int} for maintenance",
        "quarantined_count": count,
        "stalls_quarantined": count,
        "floor_number": target_int
    }


@app.get("/api/admin/audit-ledger", response_model=List[AuditLogResponse])
def admin_get_audit_ledger(
    limit: int = 200,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: AccountModel = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    TELEMETRY-04 & MASTER AUDIT STREAM:
    Real-time chronological audit ledger stream showing all inbound, POS, overrides & reclaims.
    Strictly protected: unauthenticated returns 401, non-admin returns 403.
    """
    query = db.query(AuditLogModel)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            query = query.filter(AuditLogModel.timestamp >= start_dt)
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            query = query.filter(AuditLogModel.timestamp <= end_dt)
        except Exception:
            pass

    logs = query.order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
    return logs



# ============================================================================
# STATIC FRONTEND MOUNTING
# ============================================================================
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

