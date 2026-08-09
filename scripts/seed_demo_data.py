#!/usr/bin/env python3
"""
Seed database with demo data for testing
Usage: python scripts/seed_demo_data.py
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import SessionLocal, Patient, Slot, init_db

def seed_demo_data():
    """Populate database with demo slots"""
    init_db()
    db = SessionLocal()

    try:
        # Clear existing slots (keep this for demo)
        db.query(Slot).delete()
        db.commit()

        services = [
            ("General Checkup", 30),
            ("Dental", 45),
            ("Eye Exam", 60),
            ("Lab Test", 20),
        ]

        doctors = ["Dr. Smith", "Dr. Johnson", "Dr. Williams"]

        now = datetime.utcnow()
        base_date = now.replace(hour=9, minute=0, second=0, microsecond=0)

        slot_count = 0

        # Create slots for next 30 days
        for day in range(30):
            current_date = base_date + timedelta(days=day)

            # Skip Sundays (clinic closed)
            if current_date.weekday() == 6:
                continue

            # Create slots: 9am-5pm, 30 slots per day
            for hour in range(9, 17):
                for minute in [0, 30]:
                    for service, duration in services:
                        slot = Slot(
                            doctor_or_service=service,
                            start_time=current_date.replace(hour=hour, minute=minute),
                            end_time=current_date.replace(hour=hour, minute=minute) + timedelta(minutes=duration),
                            is_available=True
                        )
                        db.add(slot)
                        slot_count += 1

        db.commit()
        print(f"✅ Created {slot_count} demo slots across 30 days")

        # Create demo patients
        demo_patients = [
            ("14155552671", "Alice Johnson"),
            ("14155552672", "Bob Smith"),
            ("14155552673", "Charlie Brown"),
        ]

        for phone, name in demo_patients:
            existing = db.query(Patient).filter(Patient.phone_number == phone).first()
            if not existing:
                patient = Patient(phone_number=phone, name=name)
                db.add(patient)

        db.commit()
        print(f"✅ Created {len(demo_patients)} demo patients")

        print("\n📊 Database seeded successfully!")
        print("You can now test with these phone numbers:")
        for phone, name in demo_patients:
            print(f"  • {phone} ({name})")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
