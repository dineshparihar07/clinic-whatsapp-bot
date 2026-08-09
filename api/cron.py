from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import os

from lib.db import get_db, Appointment, Patient, Slot, WaitingList
from lib.whatsapp import send_template, send_interactive_buttons, send_message
from lib.gemini import generate_reminder_message

router = APIRouter()
logger = logging.getLogger(__name__)

CRON_SECRET = os.getenv("CRON_SECRET", "your_cron_secret")

@router.post("/cron/reminders")
async def send_reminders(db: Session = Depends(get_db), authorization: str = Header(None)):
    """Scheduled job: send appointment reminders (24h and 2h before)"""
    try:
        # Verify cron secret if configured
        if CRON_SECRET != "your_cron_secret" and authorization != f"Bearer {CRON_SECRET}":
            logger.warning("Unauthorized cron request")
            return {"status": "error", "message": "Unauthorized"}, 403

        now = datetime.utcnow()
        count_24h = 0
        count_2h = 0

        # --- 24-Hour Reminder ---
        # Appointments between 23-25 hours away
        start_24h = now + timedelta(hours=23)
        end_24h = now + timedelta(hours=25)

        appointments_24h = db.query(Appointment).join(Slot).filter(
            Appointment.status.in_(["booked", "confirmed"]),
            Appointment.reminder_sent == False,
            Slot.start_time.between(start_24h, end_24h)
        ).all()

        for appt in appointments_24h:
            try:
                patient = appt.patient
                slot = appt.slot

                message = f"""🔔 Appointment Reminder - Tomorrow!

👨‍⚕️ {slot.doctor_or_service}
🕐 {slot.start_time.strftime('%I:%M %p')}

Please confirm or cancel below."""

                buttons = [
                    {"id": f"confirm_{appt.id}", "title": "✅ Confirm"},
                    {"id": f"cancel_{appt.id}", "title": "❌ Cancel"},
                ]

                send_interactive_buttons(patient.phone_number, message, buttons)
                appt.reminder_sent = True
                db.commit()
                count_24h += 1
                logger.info(f"Sent 24h reminder for appointment {appt.id}")

            except Exception as e:
                logger.error(f"Error sending 24h reminder for appt {appt.id}: {str(e)}")
                continue

        # --- 2-Hour Reminder ---
        # Appointments between 1.5-2.5 hours away (only for confirmed)
        start_2h = now + timedelta(hours=1.5)
        end_2h = now + timedelta(hours=2.5)

        appointments_2h = db.query(Appointment).join(Slot).filter(
            Appointment.status == "confirmed",
            Slot.start_time.between(start_2h, end_2h)
        ).all()

        for appt in appointments_2h:
            try:
                patient = appt.patient
                slot = appt.slot

                message = f"""⏰ Appointment Starting Soon!

Your {slot.doctor_or_service} appointment starts in about 2 hours.
🕐 {slot.start_time.strftime('%I:%M %p')}

See you soon! 🏥"""

                send_message(patient.phone_number, message)
                count_2h += 1
                logger.info(f"Sent 2h reminder for appointment {appt.id}")

            except Exception as e:
                logger.error(f"Error sending 2h reminder for appt {appt.id}: {str(e)}")
                continue

        logger.info(f"Reminders sent: {count_24h} (24h), {count_2h} (2h)")
        return {"status": "ok", "reminders_24h": count_24h, "reminders_2h": count_2h}

    except Exception as e:
        logger.error(f"Cron reminders job error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

@router.post("/cron/backfill-waiting-list")
async def backfill_waiting_list(db: Session = Depends(get_db), authorization: str = Header(None)):
    """Scheduled job: notify waiting list patients when slots free up"""
    try:
        # Verify cron secret if configured
        if CRON_SECRET != "your_cron_secret" and authorization != f"Bearer {CRON_SECRET}":
            logger.warning("Unauthorized cron request")
            return {"status": "error", "message": "Unauthorized"}, 403

        now = datetime.utcnow()
        count_notified = 0

        # Find waiting list entries that haven't been offered yet
        waiting_entries = db.query(WaitingList).filter(
            WaitingList.status == "waiting"
        ).all()

        for waiting in waiting_entries:
            service = waiting.service
            patient = db.query(Patient).filter(Patient.id == waiting.patient_id).first()

            if not patient:
                logger.warning(f"Patient not found for waiting list entry {waiting.id}")
                continue

            # Find an available slot for this service
            available_slot = db.query(Slot).filter(
                Slot.is_available == True,
                Slot.doctor_or_service.ilike(f"%{service}%"),
                Slot.start_time > now
            ).order_by(Slot.start_time).first()

            if not available_slot:
                logger.debug(f"No available slots for waiting patient {patient.id}, service {service}")
                continue

            try:
                message = f"""🎉 Great News!

A slot just opened up for {service}!
📅 {available_slot.start_time.strftime('%A, %B %d')}
🕐 {available_slot.start_time.strftime('%I:%M %p')}

Want to book it?"""

                buttons = [
                    {"id": f"book_slot_{available_slot.id}", "title": "✅ Book Now"},
                    {"id": "waitlist_maybe", "title": "⏳ Maybe Later"},
                ]

                send_interactive_buttons(patient.phone_number, message, buttons)

                waiting.status = "offered"
                db.commit()
                count_notified += 1
                logger.info(f"Notified waiting patient {patient.id} about slot {available_slot.id}")

            except Exception as e:
                logger.error(f"Error notifying waiting patient {patient.id}: {str(e)}")
                continue

        # Expire waiting list entries older than 30 days without being offered
        expire_date = now - timedelta(days=30)
        expired = db.query(WaitingList).filter(
            WaitingList.status == "waiting",
            WaitingList.created_at < expire_date
        ).update({"status": "expired"})
        db.commit()

        logger.info(f"Backfill: {count_notified} patients notified, {expired} entries expired")
        return {"status": "ok", "patients_notified": count_notified, "entries_expired": expired}

    except Exception as e:
        logger.error(f"Backfill job error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500
