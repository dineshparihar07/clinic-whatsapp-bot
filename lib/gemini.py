import os
import json
import logging
import google.generativeai as genai
from typing import Optional

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are an intelligent assistant for a medical clinic appointment booking system.

CLINIC SERVICES:
- General Checkup (for routine check-ups, consultations)
- Dental (for teeth, gums, oral care)
- Eye Exam (for vision, eye health)
- Lab Test (for blood work, tests)

TASK: Parse the patient's message and extract their intent and relevant details.
Return ONLY a valid JSON object (no other text) with these fields:
{
  "intent": "book" | "cancel" | "reschedule" | "faq" | "unknown",
  "service": null or one of the services listed above,
  "date": null or a date description (e.g., "tomorrow", "next Monday", "2025-03-15"),
  "time": null or a time description (e.g., "2pm", "morning", "10:30am"),
  "message": A brief, friendly response to the patient in 1-2 sentences
}

RULES:
- If intent is "book", try to identify the service they want
- If intent is "cancel" or "reschedule", acknowledge it
- For "faq", answer their question helpfully
- For "unknown", ask for clarification
- Be conversational and warm in the message field
- Always return valid JSON, never add explanations

EXAMPLES:
Input: "I want to book a dental appointment tomorrow at 2pm"
Output: {"intent": "book", "service": "Dental", "date": "tomorrow", "time": "2pm", "message": "Great! I'll help you book a Dental appointment for tomorrow at 2pm. Let me find available slots for you."}

Input: "Cancel my appointment"
Output: {"intent": "cancel", "service": null, "date": null, "time": null, "message": "I can help you cancel. Let me pull up your upcoming appointments."}
"""

def parse_intent(user_message: str) -> dict:
    """Use Gemini to parse patient intent and extract entities"""
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not configured")
            return {
                "intent": "unknown",
                "service": None,
                "date": None,
                "time": None,
                "message": "Sorry, AI service is temporarily unavailable. Please try again later.",
            }

        model = genai.GenerativeModel("gemini-pro")
        prompt = f"{SYSTEM_PROMPT}\n\nPatient message: {user_message}"

        response = model.generate_content(prompt, safety_settings=[])

        if not response.text:
            logger.warning("Empty response from Gemini")
            return {
                "intent": "unknown",
                "service": None,
                "date": None,
                "time": None,
                "message": "I didn't quite understand. Can you rephrase that?",
            }

        response_text = response.text.strip()
        logger.debug(f"Gemini response: {response_text}")

        # Try to extract and parse JSON
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)

                # Validate required fields
                if "intent" in parsed and "message" in parsed:
                    return {
                        "intent": parsed.get("intent", "unknown"),
                        "service": parsed.get("service"),
                        "date": parsed.get("date"),
                        "time": parsed.get("time"),
                        "message": parsed.get("message", ""),
                    }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON from Gemini: {str(e)}")

        # Fallback: classify by keywords
        text_lower = user_message.lower()
        if any(word in text_lower for word in ["book", "appointment", "schedule"]):
            intent = "book"
        elif any(word in text_lower for word in ["cancel", "remove", "delete"]):
            intent = "cancel"
        elif any(word in text_lower for word in ["reschedule", "change", "move"]):
            intent = "reschedule"
        else:
            intent = "unknown"

        return {
            "intent": intent,
            "service": None,
            "date": None,
            "time": None,
            "message": response_text if response_text else "How can I help you with your appointment?",
        }

    except Exception as e:
        logger.error(f"Error in parse_intent: {str(e)}", exc_info=True)
        return {
            "intent": "unknown",
            "service": None,
            "date": None,
            "time": None,
            "message": "Sorry, something went wrong. Please try again.",
        }

def generate_reminder_message(patient_name: str, service: str, appointment_time: str) -> str:
    """Generate a friendly reminder message"""
    try:
        if not GEMINI_API_KEY:
            return f"Reminder: Your {service} appointment is at {appointment_time}."

        model = genai.GenerativeModel("gemini-pro")
        prompt = f"""Write a friendly, warm appointment reminder (2 sentences max) for {patient_name} about their {service} appointment at {appointment_time}.
        Start with an emoji. Be brief and professional."""

        response = model.generate_content(prompt)
        return response.text if response.text else f"Your {service} appointment is at {appointment_time}."

    except Exception as e:
        logger.error(f"Error generating reminder: {str(e)}")
        return f"Your {service} appointment is at {appointment_time}."
