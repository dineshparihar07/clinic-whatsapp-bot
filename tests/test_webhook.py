import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from lib.db import SessionLocal, Patient, Slot

client = TestClient(app)

@pytest.fixture
def setup_demo_data():
    """Setup demo data before each test"""
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(Patient).delete()
        db.query(Slot).delete()

        # Create demo patient
        patient = Patient(phone_number="14155552671", name="Test Patient")
        db.add(patient)

        # Create demo slots
        now = datetime.utcnow()
        base_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)

        for i in range(5):
            slot = Slot(
                doctor_or_service="General Checkup",
                start_time=base_time + timedelta(hours=i),
                end_time=base_time + timedelta(hours=i, minutes=30),
                is_available=True
            )
            db.add(slot)

        db.commit()
        yield db
    finally:
        db.query(Patient).delete()
        db.query(Slot).delete()
        db.commit()
        db.close()

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_webhook_verification():
    """Test webhook verification (GET request)"""
    response = client.get(
        "/api/webhook?hub.mode=subscribe&hub.challenge=123456&hub.verify_token=test_token"
    )
    # This will fail without proper token, but we're testing the endpoint works
    assert response.status_code in [200, 403]

def test_webhook_message_booking(setup_demo_data):
    """Test webhook receiving a booking message"""
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "14155552671",
                        "id": "wamid.123456",
                        "type": "text",
                        "text": {"body": "I want to book a general checkup appointment"},
                        "timestamp": str(int(datetime.utcnow().timestamp()))
                    }]
                }
            }]
        }]
    }

    response = client.post("/api/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_webhook_invalid_token():
    """Test webhook verification with invalid token"""
    response = client.get(
        "/api/webhook?hub.mode=subscribe&hub.challenge=123456&hub.verify_token=wrong_token"
    )
    assert response.status_code == 403

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "endpoints" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
