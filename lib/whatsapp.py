import os
import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

def send_message(phone_number: str, message: str) -> dict:
    """Send a plain text message via WhatsApp"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return {"error": "WhatsApp not configured"}

    try:
        url = f"{BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message},
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()

        if response.status_code in [200, 201]:
            logger.info(f"Message sent to {phone_number}: {result.get('messages', [{}])[0].get('id', 'unknown')}")
            return result
        else:
            logger.error(f"WhatsApp API error ({response.status_code}): {result}")
            return result

    except requests.RequestException as e:
        logger.error(f"Request error sending message: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return {"error": str(e)}

def send_template(phone_number: str, template_name: str, parameters: Optional[list] = None) -> dict:
    """Send a pre-approved template (for messages outside 24h window)"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return {"error": "WhatsApp not configured"}

    try:
        url = f"{BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en_US"},
            },
        }

        if parameters:
            payload["template"]["parameters"] = {"body": {"parameters": parameters}}

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()

        if response.status_code in [200, 201]:
            logger.info(f"Template '{template_name}' sent to {phone_number}")
            return result
        else:
            logger.error(f"WhatsApp template API error ({response.status_code}): {result}")
            return result

    except Exception as e:
        logger.error(f"Error sending template: {str(e)}")
        return {"error": str(e)}

def send_interactive_buttons(phone_number: str, message: str, buttons: list) -> dict:
    """Send message with interactive buttons (max 3 buttons)"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return {"error": "WhatsApp not configured"}

    if not buttons or len(buttons) == 0:
        logger.error("No buttons provided")
        return {"error": "No buttons provided"}

    if len(buttons) > 3:
        logger.warning(f"More than 3 buttons provided, truncating to 3")
        buttons = buttons[:3]

    try:
        url = f"{BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        button_list = [
            {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"][:20]}}
            for btn in buttons
        ]

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {"buttons": button_list},
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()

        if response.status_code in [200, 201]:
            logger.info(f"Interactive message sent to {phone_number} with {len(buttons)} buttons")
            return result
        else:
            logger.error(f"WhatsApp interactive API error ({response.status_code}): {result}")
            return result

    except Exception as e:
        logger.error(f"Error sending interactive buttons: {str(e)}")
        return {"error": str(e)}

def send_list_message(phone_number: str, message: str, items: list, button_text: str = "Select") -> dict:
    """Send message with a list menu (up to 10 items)"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WhatsApp credentials not configured")
        return {"error": "WhatsApp not configured"}

    if not items or len(items) == 0:
        logger.error("No items provided for list")
        return {"error": "No items provided"}

    try:
        url = f"{BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        sections = [{
            "title": "Options",
            "rows": [
                {"id": item["id"], "title": item["title"], "description": item.get("description", "")}
                for item in items[:10]
            ]
        }]

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()

        if response.status_code in [200, 201]:
            logger.info(f"List message sent to {phone_number} with {len(items)} items")
            return result
        else:
            logger.error(f"WhatsApp list API error ({response.status_code}): {result}")
            return result

    except Exception as e:
        logger.error(f"Error sending list message: {str(e)}")
        return {"error": str(e)}
