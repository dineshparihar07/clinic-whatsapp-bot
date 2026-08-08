from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from lib.db import get_db, Appointment, Patient, Slot, WaitingList
from lib.whatsapp import send_template, send_interactive_buttons
from lib.gemini import generate_reminder_message

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/cron/reminders")
async def send_reminders(db: Session = Depends(get_db)):
    """Scheduled job: send appointment reminders"""
    try:
        # Find appointments within reminder windows (24h and 2h before start)
        now = datetime.utcnow()
        reminder_window_24h = now + timedelta(hours=24)
        reminder_window_2h = now + timedelta(hours=2)

        # Appointments needing 24-hour reminder
        appointments_24h = db.query(Appointment).join(Slot).filter(
            Appointment.status.in_(["booked", "confirmed"]),
            Appointment.reminder_sent == False,
            Slot.start_time.between(now, reminder_window_24h)
        ).all()

        for appt in appointments_24h:
            patient = appt.patient
            slot = appt.slot

            message = f"Reminder: You have a {slot.doctor_or_service} appointment at {slot.start_time.strftime('%I:%M %p')} tomorrow. Confirm or cancel?"

            buttons = [
                {"id": f"confirm_{appt.id}", "title": "Confirm"},
                {"id": f"cancel_{appt.id}", "title": "Cancel"},
            ]

            send_interactive_buttons(patient.phone_number, message, buttons)
            appt.reminder_sent = True
            db.commit()

        # Appointments needing 2-hour reminder
        appointments_2h = db.query(Appointment).join(Slot).filter(
            Appointment.status.in_(["confirmed"]),
            Slot.start_time.between(now, reminder_window_2h)
        ).all()

        for appt in appointments_2h:
            patient = appt.patient
            slot = appt.slot

            message = f"Your {slot.doctor_or_service} appointment starts in 2 hours at {slot.start_time.strftime('%I:%M %p')}."
            send_template(patient.phone_number, "appointment_reminder_2h", [patient.name, slot.start_time.strftime('%I:%M %p')])

        return {"status": "ok", "reminders_sent": len(appointments_24h)}

    except Exception as e:
        logger.error(f"Cron job error: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/cron/backfill-waiting-list")
async def backfill_waiting_list(db: Session = Depends(get_db)):
    """Scheduled job: notify waiting list patients when slots free up"""
    try:
        # Find cancelled/completed appointments
        freed_slots = db.query(Appointment).filter(
            Appointment.status.in_(["cancelled", "completed"])
        ).all()

        for appt in freed_slots:
            slot = appt.slot
            service = slot.doctor_or_service

            # Find waiting patient for this service
            waiting_patient = db.query(WaitingList).filter(
                WaitingList.service == service,
                WaitingList.status == "waiting"
            ).first()

            if waiting_patient:
                patient = db.query(Patient).filter(Patient.id == waiting_patient.patient_id).first()

                message = f"Great news! A {service} slot just opened up at {slot.start_time.strftime('%I:%M %p')}. Want to book it?"
                send_interactive_buttons(
                    patient.phone_number,
                    message,
                    [
                        {"id": f"book_slot_{slot.id}", "title": "Book Now"},
                        {"id": "maybe_later", "title": "Maybe Later"},
                    ]
                )

                waiting_patient.status = "offered"
                db.commit()

        return {"status": "ok", "waiting_list_notified": len(freed_slots)}

    except Exception as e:
        logger.error(f"Backfill job error: {str(e)}")
        return {"status": "error", "message": str(e)}
