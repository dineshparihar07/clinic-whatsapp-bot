from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional

from lib.db import get_db, Appointment, Slot, Patient, WaitingList

router = APIRouter()

# ==================== SLOTS ====================

@router.get("/admin/slots")
async def get_slots(
    db: Session = Depends(get_db),
    service: Optional[str] = Query(None),
    available_only: bool = Query(False),
    skip: int = Query(0),
    limit: int = Query(50)
):
    """Get all slots with optional filtering"""
    query = db.query(Slot)

    if service:
        query = query.filter(Slot.doctor_or_service.ilike(f"%{service}%"))

    if available_only:
        query = query.filter(Slot.is_available == True)

    total = query.count()
    slots = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "slots": [
            {
                "id": s.id,
                "service": s.doctor_or_service,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "available": s.is_available
            }
            for s in slots
        ]
    }

@router.post("/admin/slots")
async def create_slots(
    db: Session = Depends(get_db),
    service: str = Query(...),
    date: str = Query(...),  # YYYY-MM-DD
    start_time: str = Query(...),  # HH:MM
    end_time: str = Query(...),  # HH:MM
    count: int = Query(1)
):
    """Create multiple slots"""
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_hour, start_min = map(int, start_time.split(":"))
        end_hour, end_min = map(int, end_time.split(":"))

        created = []
        for i in range(count):
            slot_start = date_obj.replace(hour=start_hour, minute=start_min)
            slot_end = date_obj.replace(hour=end_hour, minute=end_min)

            slot = Slot(
                doctor_or_service=service,
                start_time=slot_start + timedelta(hours=i),
                end_time=slot_end + timedelta(hours=i),
                is_available=True
            )
            db.add(slot)
            created.append({
                "start_time": slot_start.isoformat(),
                "end_time": slot_end.isoformat()
            })

        db.commit()
        return {"message": f"Created {len(created)} slots", "slots": created}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/admin/slots/{slot_id}")
async def delete_slot(slot_id: int, db: Session = Depends(get_db)):
    """Delete a slot"""
    slot = db.query(Slot).filter(Slot.id == slot_id).first()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    db.delete(slot)
    db.commit()
    return {"message": "Slot deleted"}

# ==================== APPOINTMENTS ====================

@router.get("/admin/appointments")
async def get_appointments(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    patient_phone: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),  # YYYY-MM-DD
    to_date: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50)
):
    """Get appointments with filtering"""
    query = db.query(Appointment).join(Slot).join(Patient)

    if status:
        query = query.filter(Appointment.status == status)

    if patient_phone:
        query = query.filter(Patient.phone_number.contains(patient_phone))

    if from_date:
        from_obj = datetime.strptime(from_date, "%Y-%m-%d")
        query = query.filter(Slot.start_time >= from_obj)

    if to_date:
        to_obj = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(Slot.start_time < to_obj)

    total = query.count()
    appointments = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "appointments": [
            {
                "id": a.id,
                "patient_name": a.patient.name,
                "patient_phone": a.patient.phone_number,
                "service": a.slot.doctor_or_service,
                "start_time": a.slot.start_time.isoformat(),
                "status": a.status,
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat()
            }
            for a in appointments
        ]
    }

@router.get("/admin/appointments/{appointment_id}")
async def get_appointment_detail(appointment_id: int, db: Session = Depends(get_db)):
    """Get appointment details"""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {
        "id": appt.id,
        "patient": {
            "id": appt.patient.id,
            "name": appt.patient.name,
            "phone": appt.patient.phone_number
        },
        "slot": {
            "service": appt.slot.doctor_or_service,
            "start_time": appt.slot.start_time.isoformat(),
            "end_time": appt.slot.end_time.isoformat()
        },
        "status": appt.status,
        "reminder_sent": appt.reminder_sent,
        "created_at": appt.created_at.isoformat(),
        "updated_at": appt.updated_at.isoformat()
    }

@router.put("/admin/appointments/{appointment_id}")
async def update_appointment_status(
    appointment_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db)
):
    """Update appointment status"""
    valid_statuses = ["pending", "booked", "confirmed", "cancelled", "completed", "no_show"]

    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    old_status = appt.status
    appt.status = status
    appt.updated_at = datetime.utcnow()

    # Free up slot if cancelling
    if status == "cancelled" and old_status != "cancelled":
        slot = db.query(Slot).filter(Slot.id == appt.slot_id).first()
        if slot:
            slot.is_available = True

    db.commit()
    return {"message": f"Appointment status updated from {old_status} to {status}"}

# ==================== PATIENTS ====================

@router.get("/admin/patients")
async def get_patients(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50)
):
    """Get all patients"""
    query = db.query(Patient)

    if search:
        query = query.filter(
            or_(
                Patient.name.ilike(f"%{search}%"),
                Patient.phone_number.contains(search)
            )
        )

    total = query.count()
    patients = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "patients": [
            {
                "id": p.id,
                "name": p.name,
                "phone": p.phone_number,
                "created_at": p.created_at.isoformat()
            }
            for p in patients
        ]
    }

@router.get("/admin/patients/{patient_id}")
async def get_patient_detail(patient_id: int, db: Session = Depends(get_db)):
    """Get patient details with appointment history"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient_id
    ).all()

    return {
        "id": patient.id,
        "name": patient.name,
        "phone": patient.phone_number,
        "created_at": patient.created_at.isoformat(),
        "total_appointments": len(appointments),
        "appointments": [
            {
                "id": a.id,
                "service": a.slot.doctor_or_service,
                "start_time": a.slot.start_time.isoformat(),
                "status": a.status
            }
            for a in appointments[-10:]  # Last 10
        ]
    }

# ==================== WAITING LIST ====================

@router.get("/admin/waiting-list")
async def get_waiting_list(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50)
):
    """Get waiting list entries"""
    query = db.query(WaitingList).join(Patient)

    if status:
        query = query.filter(WaitingList.status == status)

    total = query.count()
    entries = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "entries": [
            {
                "id": e.id,
                "patient_name": e.id,
                "patient_phone": db.query(Patient).filter(Patient.id == e.patient_id).first().phone_number,
                "service": e.service,
                "status": e.status,
                "created_at": e.created_at.isoformat()
            }
            for e in entries
        ]
    }

# ==================== ANALYTICS ====================

@router.get("/admin/analytics/overview")
async def analytics_overview(db: Session = Depends(get_db)):
    """Get high-level analytics"""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Counts
    total_patients = db.query(Patient).count()
    total_appointments = db.query(Appointment).count()
    confirmed_count = db.query(Appointment).filter(Appointment.status == "confirmed").count()
    cancelled_count = db.query(Appointment).filter(Appointment.status == "cancelled").count()
    completed_count = db.query(Appointment).filter(Appointment.status == "completed").count()

    # Last 30 days
    appointments_30d = db.query(Appointment).filter(
        Appointment.created_at >= thirty_days_ago
    ).count()

    # Upcoming
    upcoming = db.query(Appointment).join(Slot).filter(
        and_(
            Appointment.status.in_(["booked", "confirmed"]),
            Slot.start_time > now
        )
    ).count()

    # Waiting list
    waiting_count = db.query(WaitingList).filter(WaitingList.status == "waiting").count()

    return {
        "patients": {
            "total": total_patients
        },
        "appointments": {
            "total": total_appointments,
            "confirmed": confirmed_count,
            "cancelled": cancelled_count,
            "completed": completed_count,
            "upcoming": upcoming,
            "last_30_days": appointments_30d
        },
        "waiting_list": {
            "total": waiting_count
        }
    }

@router.get("/admin/analytics/appointments-by-service")
async def analytics_by_service(db: Session = Depends(get_db)):
    """Get appointment counts by service"""
    from sqlalchemy import func

    results = db.query(
        Slot.doctor_or_service,
        func.count(Appointment.id).label("count")
    ).join(Appointment).group_by(Slot.doctor_or_service).all()

    return {
        "services": [
            {"service": r[0], "appointments": r[1]}
            for r in results
        ]
    }

@router.get("/admin/analytics/daily-bookings")
async def analytics_daily_bookings(
    db: Session = Depends(get_db),
    days: int = Query(30)
):
    """Get bookings per day for last N days"""
    from sqlalchemy import func

    start_date = datetime.utcnow() - timedelta(days=days)

    results = db.query(
        func.date(Appointment.created_at).label("date"),
        func.count(Appointment.id).label("count")
    ).filter(
        Appointment.created_at >= start_date
    ).group_by(
        func.date(Appointment.created_at)
    ).order_by("date").all()

    return {
        "days": days,
        "data": [
            {"date": str(r[0]), "bookings": r[1]}
            for r in results
        ]
    }
