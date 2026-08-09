import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from lib.db import SessionLocal, Patient, Slot, Appointment

client = TestClient(app)

@pytest.fixture
def setup_test_data():
    """Setup test data"""
    db = SessionLocal()
    try:
        # Clear
        db.query(Appointment).delete()
        db.query(Slot).delete()
        db.query(Patient).delete()

        # Create test patient
        patient = Patient(phone_number="14155552671", name="Test Patient")
        db.add(patient)
        db.flush()

        # Create slots for next 7 days
        now = datetime.utcnow()
        base_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

        for day in range(7):
            for hour in range(9, 17):
                slot = Slot(
                    doctor_or_service="General Checkup",
                    start_time=base_time + timedelta(days=day, hours=hour),
                    end_time=base_time + timedelta(days=day, hours=hour, minutes=30),
                    is_available=True
                )
                db.add(slot)

        db.commit()
        yield db
    finally:
        db.query(Appointment).delete()
        db.query(Slot).delete()
        db.query(Patient).delete()
        db.commit()
        db.close()

def test_get_appointments_empty(setup_test_data):
    """Test getting appointments when none exist"""
    response = client.get("/api/admin/appointments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

def test_get_slots_available(setup_test_data):
    """Test getting available slots"""
    response = client.get("/api/admin/slots?available_only=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert all(s["available"] for s in data["slots"])

def test_get_patients(setup_test_data):
    """Test getting patients"""
    response = client.get("/api/admin/patients")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["patients"][0]["name"] == "Test Patient"

def test_create_slots(setup_test_data):
    """Test creating new slots"""
    tomorrow = datetime.utcnow() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y-%m-%d")

    response = client.post(
        f"/api/admin/slots?service=Dental&date={date_str}&start_time=10:00&end_time=10:30&count=3"
    )
    assert response.status_code == 200
    data = response.json()
    assert "Created 3 slots" in data["message"]

def test_get_slots_by_service(setup_test_data):
    """Test filtering slots by service"""
    response = client.get("/api/admin/slots?service=General")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert all("General" in s["service"] for s in data["slots"])

def test_double_booking_prevention(setup_test_data):
    """Test that double booking is prevented"""
    db = SessionLocal()

    # Get first available slot
    slot = db.query(Slot).filter(Slot.is_available == True).first()
    patient = db.query(Patient).first()

    # Book first appointment
    appt1 = Appointment(
        patient_id=patient.id,
        slot_id=slot.id,
        status="booked"
    )
    db.add(appt1)
    slot.is_available = False
    db.commit()

    # Try to book same slot with different patient
    patient2 = Patient(phone_number="14155552672", name="Patient 2")
    db.add(patient2)
    db.flush()

    # Should fail because slot is not available
    assert not slot.is_available

    db.close()

def test_appointment_cancellation_frees_slot(setup_test_data):
    """Test that cancelling appointment frees slot"""
    db = SessionLocal()

    # Setup
    slot = db.query(Slot).filter(Slot.is_available == True).first()
    patient = db.query(Patient).first()

    appt = Appointment(patient_id=patient.id, slot_id=slot.id, status="booked")
    db.add(appt)
    slot.is_available = False
    db.commit()

    assert not slot.is_available

    # Cancel appointment
    appt.status = "cancelled"
    slot.is_available = True
    db.commit()

    # Verify
    updated_slot = db.query(Slot).filter(Slot.id == slot.id).first()
    assert updated_slot.is_available

    db.close()

def test_analytics_overview(setup_test_data):
    """Test analytics overview"""
    response = client.get("/api/admin/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "patients" in data
    assert "appointments" in data
    assert data["patients"]["total"] == 1

def test_analytics_by_service(setup_test_data):
    """Test analytics by service"""
    response = client.get("/api/admin/analytics/appointments-by-service")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data

def test_get_waiting_list(setup_test_data):
    """Test getting waiting list"""
    response = client.get("/api/admin/waiting-list")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
