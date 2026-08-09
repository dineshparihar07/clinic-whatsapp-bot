from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
import os
from datetime import datetime, timedelta
import logging
import json

from lib.db import get_db, Patient, Appointment, Slot, ConversationState, WaitingList
from lib.whatsapp import send_message, send_interactive_buttons
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
        logger.warning("Invalid webhook verify token attempt")
        return PlainTextResponse("Unauthorized", status_code=403)

    logger.info("Webhook verified successfully")
    return PlainTextResponse(hub_challenge)

@router.post("/webhook")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp messages (POST request)"""
    try:
        data = await request.json()
        logger.debug(f"Webhook payload: {json.dumps(data)}")

        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            logger.debug("No messages in webhook payload")
            return {"status": "ok"}

        message = messages[0]
        phone_number = message.get("from")
        message_id = message.get("id")
        message_type = message.get("type", "text")
        timestamp = message.get("timestamp")

        logger.info(f"Processing message from {phone_number}: type={message_type}")

        # Get or create patient
        patient = db.query(Patient).filter(Patient.phone_number == phone_number).first()
        if not patient:
            patient = Patient(phone_number=phone_number, name=f"Patient {phone_number}")
            db.add(patient)
            db.commit()
            db.refresh(patient)
            logger.info(f"Created new patient: {phone_number}")

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
            db.flush()

        # Parse message based on type
        if message_type == "text":
            user_message = message.get("text", {}).get("body", "").strip()
        elif message_type == "interactive":
            button_id = message.get("interactive", {}).get("button_reply", {}).get("id", "")
            user_message = button_id
        else:
            logger.warning(f"Unsupported message type: {message_type}")
            return {"status": "ok"}

        if not user_message:
            return {"status": "ok"}

        # Use Gemini to understand intent
        parsed = parse_intent(user_message)
        intent = parsed.get("intent")

        logger.info(f"Parsed intent: {intent} from message: {user_message}")

        # Handle button responses (slot selection, confirm/cancel)
        if "slot_" in user_message:
            handle_slot_selection(db, patient, user_message, phone_number)
        elif "confirm_" in user_message:
            handle_confirm_appointment(db, patient, user_message, phone_number)
        elif "cancel_" in user_message:
            handle_cancel_from_reminder(db, patient, user_message, phone_number)
        elif "book_slot_" in user_message:
            handle_waiting_list_booking(db, patient, user_message, phone_number)
        elif intent == "book":
            handle_booking(db, patient, parsed, phone_number, conv_state)
        elif intent == "cancel":
            handle_cancellation(db, patient, phone_number)
        elif intent == "reschedule":
            handle_reschedule(db, patient, phone_number)
        elif intent == "faq":
            send_message(phone_number, parsed.get("message", "How can I help you?"))
        else:
            send_message(phone_number, parsed.get("message", "I didn't understand that. Try: 'I want to book an appointment'"))

        # Update conversation state
        conv_state.current_step = intent
        conv_state.context_json = parsed
        conv_state.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Successfully processed message from {phone_number}")
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

def handle_booking(db: Session, patient: Patient, parsed: dict, phone_number: str, conv_state: ConversationState):
    """Handle appointment booking - show available slots"""
    service = parsed.get("service") or "General Checkup"
    desired_date = parsed.get("date")

    # Query available slots for the service
    query = db.query(Slot).filter(
        Slot.is_available == True,
        Slot.doctor_or_service.ilike(f"%{service}%")
    )

    available_slots = query.order_by(Slot.start_time).limit(5).all()

    if not available_slots:
        logger.info(f"No slots available for {service}")
        send_message(phone_number, f"Sorry, no available {service} slots right now. Want to join our waiting list?")

        # Offer waiting list option
        buttons = [
            {"id": "waitlist_yes", "title": "Yes, add me"},
            {"id": "waitlist_no", "title": "No thanks"},
        ]
        send_interactive_buttons(phone_number, "We'll notify you when slots open up!", buttons)
        return

    logger.info(f"Found {len(available_slots)} slots for {service}")

    # Store slot options in conversation state
    conv_state.context_json["available_slots"] = [
        {"id": slot.id, "time": slot.start_time.isoformat(), "service": slot.doctor_or_service}
        for slot in available_slots[:3]
    ]
    conv_state.current_step = "selecting_slot"

    # Send slot options as interactive buttons
    buttons = [
        {
            "id": f"slot_{slot.id}",
            "title": f"{slot.start_time.strftime('%a %I:%M %p')}"
        }
        for slot in available_slots[:3]
    ]

    send_interactive_buttons(
        phone_number,
        f"📅 Here are available {service} slots. Pick one:",
        buttons
    )

def handle_slot_selection(db: Session, patient: Patient, button_id: str, phone_number: str):
    """Handle patient selecting a slot from available options"""
    try:
        slot_id = int(button_id.split("_")[1])
        slot = db.query(Slot).filter(Slot.id == slot_id).first()

        if not slot:
            send_message(phone_number, "❌ Slot not found. Please try again.")
            return

        if not slot.is_available:
            send_message(phone_number, "❌ Sorry, this slot is no longer available. Try another one.")
            return

        # Lock the slot (mark as unavailable) and create appointment
        slot.is_available = False
        appointment = Appointment(
            patient_id=patient.id,
            slot_id=slot.id,
            status="booked"
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        logger.info(f"Appointment booked: patient={patient.id}, slot={slot.id}, appt={appointment.id}")

        # Send confirmation
        confirmation_msg = f"""✅ Appointment Confirmed!

📅 Date: {slot.start_time.strftime('%A, %B %d')}
🕐 Time: {slot.start_time.strftime('%I:%M %p')}
👨‍⚕️ Service: {slot.doctor_or_service}

Your appointment ID: {appointment.id}
You'll receive a reminder 24 hours before."""

        send_message(phone_number, confirmation_msg)

    except Exception as e:
        logger.error(f"Error in slot selection: {str(e)}")
        send_message(phone_number, "❌ Error booking appointment. Please try again.")

def handle_confirm_appointment(db: Session, patient: Patient, button_id: str, phone_number: str):
    """Handle patient confirming appointment from reminder"""
    try:
        appt_id = int(button_id.split("_")[1])
        appt = db.query(Appointment).filter(Appointment.id == appt_id).first()

        if not appt:
            send_message(phone_number, "❌ Appointment not found.")
            return

        appt.status = "confirmed"
        db.commit()
        logger.info(f"Appointment confirmed: {appt_id}")
        send_message(phone_number, "✅ Thanks for confirming! See you soon! 👋")

    except Exception as e:
        logger.error(f"Error confirming appointment: {str(e)}")
        send_message(phone_number, "❌ Error confirming appointment.")

def handle_cancel_from_reminder(db: Session, patient: Patient, button_id: str, phone_number: str):
    """Handle patient cancelling appointment from reminder"""
    try:
        appt_id = int(button_id.split("_")[1])
        appt = db.query(Appointment).filter(Appointment.id == appt_id).first()

        if not appt:
            send_message(phone_number, "❌ Appointment not found.")
            return

        appt.status = "cancelled"
        db.commit()

        # Free up the slot
        slot = db.query(Slot).filter(Slot.id == appt.slot_id).first()
        if slot:
            slot.is_available = True
            db.commit()

        logger.info(f"Appointment cancelled: {appt_id}, slot freed: {slot.id}")
        send_message(phone_number, "❌ Your appointment has been cancelled. We've freed up the slot.")

    except Exception as e:
        logger.error(f"Error cancelling appointment: {str(e)}")
        send_message(phone_number, "❌ Error cancelling appointment.")

def handle_cancellation(db: Session, patient: Patient, phone_number: str):
    """Handle appointment cancellation - show upcoming appointments"""
    upcoming = db.query(Appointment).filter(
        Appointment.patient_id == patient.id,
        Appointment.status.in_(["booked", "confirmed"])
    ).all()

    if not upcoming:
        send_message(phone_number, "You don't have any upcoming appointments to cancel.")
        return

    if len(upcoming) == 1:
        appt = upcoming[0]
        slot = db.query(Slot).filter(Slot.id == appt.slot_id).first()
        msg = f"Are you sure? This will cancel your appointment on {slot.start_time.strftime('%A at %I:%M %p')}"

        buttons = [
            {"id": f"cancel_{appt.id}", "title": "Yes, cancel"},
            {"id": "cancel_no", "title": "No, keep it"},
        ]
        send_interactive_buttons(phone_number, msg, buttons)
    else:
        send_message(phone_number, "You have multiple appointments. Reply with 'cancel' and which one you want to cancel.")

def handle_waiting_list_booking(db: Session, patient: Patient, button_id: str, phone_number: str):
    """Handle waiting list patient accepting a freed-up slot"""
    try:
        slot_id = int(button_id.split("_")[2])
        slot = db.query(Slot).filter(Slot.id == slot_id).first()

        if not slot or not slot.is_available:
            send_message(phone_number, "❌ Slot no longer available. Sorry!")
            return

        slot.is_available = False
        appointment = Appointment(patient_id=patient.id, slot_id=slot.id, status="booked")
        db.add(appointment)

        # Mark waiting list item as booked
        waiting = db.query(WaitingList).filter(WaitingList.patient_id == patient.id).first()
        if waiting:
            waiting.status = "booked"

        db.commit()
        logger.info(f"Waiting list patient booked: patient={patient.id}, slot={slot.id}")

        msg = f"""✅ Slot Booked!

{slot.start_time.strftime('%A, %B %d at %I:%M %p')}
Service: {slot.doctor_or_service}

See you then! 🎉"""
        send_message(phone_number, msg)

    except Exception as e:
        logger.error(f"Error in waiting list booking: {str(e)}")
        send_message(phone_number, "❌ Error booking slot.")

def handle_reschedule(db: Session, patient: Patient, phone_number: str):
    """Handle appointment rescheduling"""
    send_message(phone_number, "🔄 To reschedule, please cancel your current appointment and book a new one. Sorry for the extra steps!")
