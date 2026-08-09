import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format"""
    phone = phone.replace(" ", "").replace("-", "").replace("+", "")
    if not phone.startswith("1"):
        phone = "1" + phone
    if not phone.startswith("1"):
        phone = phone
    return phone if phone.startswith("+") else "+" + phone

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    phone = phone.replace(" ", "").replace("-", "").replace("+", "")
    return len(phone) >= 10 and len(phone) <= 15 and phone.isdigit()

def parse_date_string(date_str: Optional[str]) -> Optional[datetime]:
    """Parse relative date strings like 'tomorrow', 'next Monday', etc."""
    if not date_str:
        return None

    date_str = date_str.lower().strip()
    now = datetime.utcnow()

    # Today
    if date_str in ["today"]:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Tomorrow
    if date_str in ["tomorrow", "next day"]:
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Days of week
    days = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }

    for day_name, day_num in days.items():
        if day_name in date_str:
            current_day = now.weekday()
            days_ahead = day_num - current_day
            if days_ahead <= 0:
                days_ahead += 7
            target_date = now + timedelta(days=days_ahead)
            return target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Try parsing ISO format
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            continue

    logger.warning(f"Could not parse date string: {date_str}")
    return None

def parse_time_string(time_str: Optional[str]) -> Optional[str]:
    """Parse time strings like '2pm', '14:30', 'morning', etc."""
    if not time_str:
        return None

    time_str = time_str.lower().strip()

    # Time slots
    time_slots = {
        "morning": "09:00",
        "mid-morning": "10:30",
        "late morning": "11:30",
        "noon": "12:00",
        "afternoon": "14:00",
        "early afternoon": "13:00",
        "late afternoon": "16:00",
        "evening": "18:00",
    }

    if time_str in time_slots:
        return time_slots[time_str]

    # Parse "2pm", "2:30pm", etc.
    time_str = time_str.replace("am", "").replace("pm", "").strip()

    try:
        if ":" in time_str:
            hour, minute = time_str.split(":")
            return f"{int(hour):02d}:{int(minute):02d}"
        else:
            hour = int(time_str)
            return f"{hour:02d}:00"
    except ValueError:
        logger.warning(f"Could not parse time string: {time_str}")
        return None

def get_next_available_slot_time(preferred_time: Optional[str] = None) -> str:
    """Get the next available slot time based on preferred time"""
    slots = [
        "09:00", "10:00", "11:00", "12:00",
        "14:00", "15:00", "16:00", "17:00"
    ]

    if preferred_time:
        parsed = parse_time_string(preferred_time)
        if parsed and parsed in slots:
            return parsed

    return "10:00"

def format_appointment_details(
    service: str,
    start_time: datetime,
    doctor: Optional[str] = None
) -> str:
    """Format appointment details for display"""
    msg = f"""
📋 Appointment Details
━━━━━━━━━━━━━━━━━━━━
👨‍⚕️ Service: {service}
📅 Date: {start_time.strftime('%A, %B %d, %Y')}
🕐 Time: {start_time.strftime('%I:%M %p')}
"""
    if doctor:
        msg += f"👨‍⚕️ Doctor: {doctor}\n"

    return msg

def calculate_reminder_times(appointment_time: datetime) -> dict:
    """Calculate when reminders should be sent"""
    now = datetime.utcnow()
    time_until = appointment_time - now

    return {
        "appointment_time": appointment_time,
        "time_until_appointment": time_until,
        "send_24h_reminder": appointment_time - timedelta(hours=24),
        "send_2h_reminder": appointment_time - timedelta(hours=2),
        "should_send_24h": 23 <= (time_until.total_seconds() / 3600) <= 25,
        "should_send_2h": 1.5 <= (time_until.total_seconds() / 3600) <= 2.5,
    }

def minutes_until_appointment(appointment_time: datetime) -> int:
    """Calculate minutes until appointment"""
    now = datetime.utcnow()
    delta = appointment_time - now
    return int(delta.total_seconds() / 60)
