from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session
import os
from datetime import datetime
import logging

from lib.db import get_db, Patient, Appointment, Slot, ConversationState
from lib.whatsapp import verify_webhook, send_message, send_interactive_buttons
from lib.gemini import parse_intent

router = APIRouter()
logger = logging.getLogger(__name__)

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "your_verify_token")

@router.get("/webhook")
async def verify(
    hub_mode: str = Query(...),
    hub_challenge: str = Query(...),
    hub_verify_token: str = Query(...),
):
    """WhatsApp webhook verification (GET request)"""
    if hub_verify_token != WHATSAPP_VERIFY_TOKEN:
        return {"status": "error", "message": "Invalid verify token"}

    return int(hub_challenge)

@router.post("/webhook")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp messages (POST request)"""
    data = await request.json()

    try:
        # Parse incoming message
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        message = messages[0]
        phone_number = message.get("from")
        message_type = message.get("type", "text")

        # Get or create patient
        patient = db.query(Patient).filter(Patient.phone_number == phone_number).first()
        if not patient:
            patient = Patient(phone_number=phone_number, name=f"Patient {phone_number}")
            db.add(patient)
            db.commit()
            db.refresh(patient)

        # Get or create conversation state
        conv_state = db.query(ConversationState).filter(
            ConversationState.phone_number == phone_number
        ).first()
        if not conv_state:
            conv_state = ConversationState(
                phone_number=phone_number,
                current_step="awaiting_intent",
                context_json={}
            )
            db.add(conv_state)

        # Parse message based on type
        if message_type == "text":
            user_message = message.get("text", {}).get("body", "")
        elif message_type == "interactive":
            user_message = message.get("interactive", {}).get("button_reply", {}).get("id", "")
        else:
            user_message = ""

        # Use Gemini to understand intent
        parsed = parse_intent(user_message)
        intent = parsed.get("intent")

        # Handle based on intent
        if intent == "book":
            handle_booking(db, patient, parsed, phone_number)
        elif intent == "cancel":
            handle_cancellation(db, patient, phone_number)
        elif intent == "reschedule":
            handle_reschedule(db, patient, phone_number)
        else:
            send_message(phone_number, parsed.get("message", "I didn't understand that. Please try again."))

        # Update conversation state
        conv_state.current_step = intent
        conv_state.context_json = parsed
        conv_state.updated_at = datetime.utcnow()
        db.commit()

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_booking(db: Session, patient: Patient, parsed: dict, phone_number: str):
    """Handle appointment booking"""
    service = parsed.get("service")
    desired_date = parsed.get("date")

    # Query available slots
    available_slots = db.query(Slot).filter(
        Slot.is_available == True,
        Slot.doctor_or_service == service
    ).limit(5).all()

    if not available_slots:
        send_message(phone_number, f"Sorry, no available slots for {service}. Try another date?")
        return

    # Send slot options as interactive buttons
    buttons = [
        {
            "id": f"slot_{slot.id}",
            "title": f"{slot.start_time.strftime('%I:%M %p')}"
        }
        for slot in available_slots[:3]
    ]

    send_interactive_buttons(
        phone_number,
        f"Here are available {service} slots:",
        buttons
    )

def handle_cancellation(db: Session, patient: Patient, phone_number: str):
    """Handle appointment cancellation"""
    upcoming = db.query(Appointment).filter(
        Appointment.patient_id == patient.id,
        Appointment.status.in_(["booked", "confirmed"])
    ).first()

    if not upcoming:
        send_message(phone_number, "You don't have any upcoming appointments to cancel.")
        return

    upcoming.status = "cancelled"
    db.commit()

    # Free up the slot
    slot = db.query(Slot).filter(Slot.id == upcoming.slot_id).first()
    if slot:
        slot.is_available = True
        db.commit()

    send_message(phone_number, "Your appointment has been cancelled. Slot is now available.")

def handle_reschedule(db: Session, patient: Patient, phone_number: str):
    """Handle appointment rescheduling"""
    send_message(phone_number, "Rescheduling coming soon. Please cancel and rebook for now.")
