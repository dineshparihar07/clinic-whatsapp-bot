import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
import os

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "phone_number"):
            log_data["phone_number"] = record.phone_number
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)

class EventLogger:
    """Log important events for monitoring"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def message_received(self, phone_number: str, message_type: str, intent: str):
        """Log when a message is received"""
        self.logger.info(
            f"Message received from {phone_number}",
            extra={
                "event": "message_received",
                "phone_number": phone_number,
                "message_type": message_type,
                "intent": intent
            }
        )

    def appointment_booked(self, patient_id: int, slot_id: int, appointment_id: int):
        """Log when appointment is booked"""
        self.logger.info(
            f"Appointment booked",
            extra={
                "event": "appointment_booked",
                "patient_id": patient_id,
                "slot_id": slot_id,
                "appointment_id": appointment_id
            }
        )

    def appointment_cancelled(self, appointment_id: int, reason: Optional[str] = None):
        """Log when appointment is cancelled"""
        self.logger.info(
            f"Appointment cancelled",
            extra={
                "event": "appointment_cancelled",
                "appointment_id": appointment_id,
                "reason": reason
            }
        )

    def reminder_sent(self, patient_id: int, appointment_id: int, reminder_type: str):
        """Log when reminder is sent"""
        self.logger.info(
            f"Reminder sent",
            extra={
                "event": "reminder_sent",
                "patient_id": patient_id,
                "appointment_id": appointment_id,
                "reminder_type": reminder_type
            }
        )

    def waiting_list_notified(self, patient_id: int, slot_id: int):
        """Log when waiting list patient is notified"""
        self.logger.info(
            f"Waiting list patient notified",
            extra={
                "event": "waiting_list_notified",
                "patient_id": patient_id,
                "slot_id": slot_id
            }
        )

    def whatsapp_error(self, error_code: int, error_message: str, phone_number: str):
        """Log WhatsApp API errors"""
        self.logger.error(
            f"WhatsApp API error",
            extra={
                "event": "whatsapp_error",
                "error_code": error_code,
                "error_message": error_message,
                "phone_number": phone_number
            }
        )

    def database_error(self, error: Exception, context: str):
        """Log database errors"""
        self.logger.error(
            f"Database error: {context}",
            extra={
                "event": "database_error",
                "error": str(error),
                "context": context
            },
            exc_info=True
        )

    def gemini_error(self, error: Exception, user_message: str):
        """Log Gemini API errors"""
        self.logger.error(
            f"Gemini API error",
            extra={
                "event": "gemini_error",
                "error": str(error),
                "user_message": user_message[:100]
            },
            exc_info=True
        )

class MetricsCollector:
    """Collect metrics for monitoring"""

    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.timings: Dict[str, list] = {}
        self.last_error: Optional[str] = None

    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter"""
        if metric_name not in self.counters:
            self.counters[metric_name] = 0
        self.counters[metric_name] += value

    def record_timing(self, metric_name: str, duration_ms: float):
        """Record timing metric"""
        if metric_name not in self.timings:
            self.timings[metric_name] = []
        self.timings[metric_name].append(duration_ms)
        # Keep only last 100 measurements
        if len(self.timings[metric_name]) > 100:
            self.timings[metric_name] = self.timings[metric_name][-100:]

    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics"""
        stats = {
            "counters": self.counters.copy(),
            "timings": {}
        }

        for metric_name, timings in self.timings.items():
            if timings:
                stats["timings"][metric_name] = {
                    "count": len(timings),
                    "min": min(timings),
                    "max": max(timings),
                    "avg": sum(timings) / len(timings)
                }

        return stats

    def record_error(self, error_message: str):
        """Record last error"""
        self.last_error = f"{datetime.utcnow().isoformat()}: {error_message}"

# Global instances
def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup structured logging"""
    logger = logging.getLogger("clinic_bot")
    logger.setLevel(level)

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Use JSON formatter for structured logging
    if os.getenv("ENV") == "production":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)

    # Remove existing handlers and add new one
    logger.handlers = []
    logger.addHandler(console_handler)

    return logger

# Initialize
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
event_logger = EventLogger(logger)
metrics = MetricsCollector()
