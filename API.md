# API Documentation

Complete API reference for Clinic WhatsApp Bot.

## Base URL

```
Development: http://localhost:3000
Production: https://your-app.onrender.com
```

## Authentication

### Webhook Verification
- Token-based: `WHATSAPP_VERIFY_TOKEN`
- Passed as query parameter: `hub.verify_token`

### Cron Job Security
- Bearer token: `CRON_SECRET`
- Passed in Authorization header: `Bearer {CRON_SECRET}`

### Admin API
- No authentication (add later via API key if needed)
- Restrict network access via firewall

---

## WhatsApp Webhooks

### GET /api/webhook
Webhook verification handshake (WhatsApp requirement).

**Query Parameters:**
- `hub.mode` (required) — `subscribe`
- `hub.challenge` (required) — Challenge string
- `hub.verify_token` (required) — Must match `WHATSAPP_VERIFY_TOKEN`

**Response (200):**
```
{hub.challenge}
```

**Example:**
```bash
curl "http://localhost:3000/api/webhook?hub.mode=subscribe&hub.challenge=12345&hub.verify_token=my_token"
# Returns: 12345
```

### POST /api/webhook
Handle incoming WhatsApp messages.

**Body:**
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "14155552671",
          "id": "wamid.123456",
          "type": "text",
          "text": {"body": "I want to book an appointment"},
          "timestamp": "1234567890"
        }]
      }
    }]
  }]
}
```

**Response (200):**
```json
{
  "status": "ok"
}
```

**Message Types Supported:**
- `text` — Plain text message
- `interactive` — Button/list menu response

**Flow:**
1. Patient sends message
2. Bot parses intent with Gemini
3. Bot shows available slots (if booking)
4. Patient clicks slot or button
5. Bot confirms/processes action

---

## Cron Jobs

### POST /api/cron/reminders
Send appointment reminders (24h and 2h before).

**Headers:**
```
Authorization: Bearer {CRON_SECRET}
```

**Response (200):**
```json
{
  "status": "ok",
  "reminders_24h": 5,
  "reminders_2h": 3
}
```

**Usage:**
```bash
curl -X POST http://localhost:3000/api/cron/reminders \
  -H "Authorization: Bearer your_cron_secret"
```

**Schedule:** Every 15-30 minutes

### POST /api/cron/backfill-waiting-list
Notify waiting patients when slots become available.

**Headers:**
```
Authorization: Bearer {CRON_SECRET}
```

**Response (200):**
```json
{
  "status": "ok",
  "patients_notified": 2,
  "entries_expired": 1
}
```

**Usage:**
```bash
curl -X POST http://localhost:3000/api/cron/backfill-waiting-list \
  -H "Authorization: Bearer your_cron_secret"
```

**Schedule:** Every 1 hour

---

## Admin APIs

### Appointments

#### GET /api/admin/appointments
List all appointments with filtering.

**Query Parameters:**
- `status` — Filter by status (booked, confirmed, cancelled, etc.)
- `patient_phone` — Filter by phone number
- `from_date` — Start date (YYYY-MM-DD)
- `to_date` — End date (YYYY-MM-DD)
- `skip` — Pagination offset (default: 0)
- `limit` — Results per page (default: 50)

**Response (200):**
```json
{
  "total": 42,
  "skip": 0,
  "limit": 50,
  "appointments": [
    {
      "id": 1,
      "patient_name": "John Doe",
      "patient_phone": "14155552671",
      "service": "General Checkup",
      "start_time": "2025-01-20T10:00:00",
      "status": "confirmed",
      "created_at": "2025-01-15T08:30:00",
      "updated_at": "2025-01-15T08:35:00"
    }
  ]
}
```

**Examples:**
```bash
# Get all confirmed appointments
curl "http://localhost:3000/api/admin/appointments?status=confirmed"

# Get appointments for this week
curl "http://localhost:3000/api/admin/appointments?from_date=2025-01-20&to_date=2025-01-27"

# Find patient by phone
curl "http://localhost:3000/api/admin/appointments?patient_phone=14155552671"
```

#### GET /api/admin/appointments/{appointment_id}
Get single appointment details.

**Response (200):**
```json
{
  "id": 1,
  "patient": {
    "id": 5,
    "name": "John Doe",
    "phone": "14155552671"
  },
  "slot": {
    "service": "General Checkup",
    "start_time": "2025-01-20T10:00:00",
    "end_time": "2025-01-20T10:30:00"
  },
  "status": "confirmed",
  "reminder_sent": true,
  "created_at": "2025-01-15T08:30:00",
  "updated_at": "2025-01-15T08:35:00"
}
```

#### PUT /api/admin/appointments/{appointment_id}
Update appointment status.

**Query Parameters:**
- `status` — New status (pending, booked, confirmed, cancelled, completed, no_show)

**Response (200):**
```json
{
  "message": "Appointment status updated from booked to confirmed"
}
```

**Example:**
```bash
# Cancel appointment
curl -X PUT "http://localhost:3000/api/admin/appointments/1?status=cancelled"
```

### Slots

#### GET /api/admin/slots
List all slots with filtering.

**Query Parameters:**
- `service` — Filter by service name
- `available_only` — Show only available (true/false)
- `skip` — Pagination offset
- `limit` — Results per page

**Response (200):**
```json
{
  "total": 120,
  "skip": 0,
  "limit": 50,
  "slots": [
    {
      "id": 1,
      "service": "General Checkup",
      "start_time": "2025-01-20T09:00:00",
      "end_time": "2025-01-20T09:30:00",
      "available": true
    }
  ]
}
```

**Examples:**
```bash
# Get all available Dental slots
curl "http://localhost:3000/api/admin/slots?service=Dental&available_only=true"

# Get all slots
curl "http://localhost:3000/api/admin/slots"
```

#### POST /api/admin/slots
Create new slots.

**Query Parameters:**
- `service` — Service name
- `date` — Date (YYYY-MM-DD)
- `start_time` — Start time (HH:MM)
- `end_time` — End time (HH:MM)
- `count` — Number of slots to create

**Response (200):**
```json
{
  "message": "Created 3 slots",
  "slots": [
    {"start_time": "2025-01-20T10:00:00", "end_time": "2025-01-20T10:30:00"},
    {"start_time": "2025-01-21T10:00:00", "end_time": "2025-01-21T10:30:00"},
    {"start_time": "2025-01-22T10:00:00", "end_time": "2025-01-22T10:30:00"}
  ]
}
```

**Example:**
```bash
# Create 3 Dental slots starting tomorrow at 2pm
curl -X POST "http://localhost:3000/api/admin/slots?service=Dental&date=2025-01-20&start_time=14:00&end_time=14:30&count=3"
```

#### DELETE /api/admin/slots/{slot_id}
Delete a slot.

**Response (200):**
```json
{
  "message": "Slot deleted"
}
```

### Patients

#### GET /api/admin/patients
List all patients.

**Query Parameters:**
- `search` — Search by name or phone
- `skip` — Pagination offset
- `limit` — Results per page

**Response (200):**
```json
{
  "total": 42,
  "skip": 0,
  "limit": 50,
  "patients": [
    {
      "id": 1,
      "name": "John Doe",
      "phone": "14155552671",
      "created_at": "2025-01-15T08:30:00"
    }
  ]
}
```

#### GET /api/admin/patients/{patient_id}
Get patient details with appointment history.

**Response (200):**
```json
{
  "id": 1,
  "name": "John Doe",
  "phone": "14155552671",
  "created_at": "2025-01-15T08:30:00",
  "total_appointments": 5,
  "appointments": [
    {
      "id": 1,
      "service": "General Checkup",
      "start_time": "2025-01-20T10:00:00",
      "status": "confirmed"
    }
  ]
}
```

### Waiting List

#### GET /api/admin/waiting-list
List waiting list entries.

**Query Parameters:**
- `status` — Filter by status (waiting, offered, expired)
- `skip` — Pagination offset
- `limit` — Results per page

**Response (200):**
```json
{
  "total": 12,
  "skip": 0,
  "limit": 50,
  "entries": [
    {
      "id": 1,
      "patient_name": "Jane Smith",
      "patient_phone": "14155552672",
      "service": "Dental",
      "status": "waiting",
      "created_at": "2025-01-15T09:00:00"
    }
  ]
}
```

---

## Analytics APIs

### GET /api/admin/analytics/overview
High-level analytics summary.

**Response (200):**
```json
{
  "patients": {
    "total": 42
  },
  "appointments": {
    "total": 125,
    "confirmed": 98,
    "cancelled": 15,
    "completed": 10,
    "upcoming": 3,
    "last_30_days": 32
  },
  "waiting_list": {
    "total": 8
  }
}
```

### GET /api/admin/analytics/appointments-by-service
Appointment breakdown by service.

**Response (200):**
```json
{
  "services": [
    {"service": "General Checkup", "appointments": 45},
    {"service": "Dental", "appointments": 38},
    {"service": "Eye Exam", "appointments": 25},
    {"service": "Lab Test", "appointments": 17}
  ]
}
```

### GET /api/admin/analytics/daily-bookings
Daily booking trend.

**Query Parameters:**
- `days` — Number of days (default: 30)

**Response (200):**
```json
{
  "days": 30,
  "data": [
    {"date": "2024-12-17", "bookings": 3},
    {"date": "2024-12-18", "bookings": 5},
    {"date": "2024-12-19", "bookings": 2}
  ]
}
```

---

## Monitoring APIs

### GET /health
Health check endpoint.

**Response (200):**
```json
{
  "status": "ok",
  "service": "Clinic WhatsApp Bot",
  "version": "0.1.0"
}
```

### GET /api/metrics
Application metrics and performance data.

**Response (200):**
```json
{
  "status": "ok",
  "metrics": {
    "counters": {
      "messages_received": 152,
      "appointments_booked": 48,
      "reminders_sent": 16
    },
    "timings": {
      "webhook_processing": {
        "count": 152,
        "min": 23,
        "max": 1245,
        "avg": 187
      },
      "gemini_processing": {
        "count": 152,
        "min": 450,
        "max": 3200,
        "avg": 1250
      }
    }
  },
  "last_error": "2025-01-15T10:30:45: WhatsApp API timeout"
}
```

### GET /api/metrics/counters
Get counter metrics only.

### GET /api/metrics/timings
Get timing metrics only.

### POST /api/metrics/reset
Reset all metrics to zero.

**Response (200):**
```json
{
  "status": "ok",
  "message": "Metrics reset"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid status. Must be one of: pending, booked, confirmed, cancelled, completed, no_show"
}
```

### 403 Forbidden
```json
{
  "detail": "Unauthorized"
}
```

### 404 Not Found
```json
{
  "detail": "Appointment not found"
}
```

### 500 Internal Server Error
```json
{
  "status": "error",
  "message": "Database connection failed"
}
```

---

## Rate Limiting

- No rate limiting implemented (add if needed)
- WhatsApp API: ~1000 messages/second per number ID
- Gemini API: Depends on quota (check Google Cloud)

---

## Pagination

For endpoints returning lists:
- Default `limit`: 50
- Max `limit`: 1000
- Use `skip` to paginate

Example:
```bash
# Get items 50-100
curl "http://localhost:3000/api/admin/appointments?skip=50&limit=50"

# Get next page
curl "http://localhost:3000/api/admin/appointments?skip=100&limit=50"
```

---

## Date/Time Format

All timestamps are ISO 8601 format:
```
2025-01-15T10:30:45
2025-01-15T10:30:45.123Z
```

Date parameters (YYYY-MM-DD):
```
2025-01-15
```

Time parameters (HH:MM):
```
14:30
09:00
```

---

## Testing with cURL

### Test Health
```bash
curl http://localhost:3000/health
```

### Test Webhook Verification
```bash
curl "http://localhost:3000/api/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=my_token"
```

### Test Create Slot
```bash
curl -X POST "http://localhost:3000/api/admin/slots?service=Dental&date=2025-01-20&start_time=14:00&end_time=14:30&count=1"
```

### Test Get Appointments
```bash
curl "http://localhost:3000/api/admin/appointments?status=confirmed"
```

### Test Metrics
```bash
curl http://localhost:3000/api/metrics | jq .
```

---

## Postman Collection

[Download Postman Collection](postman-collection.json) (auto-generated from OpenAPI spec)

Or use Swagger UI:
```
http://localhost:3000/docs
```

---

**Last Updated:** 2025-01-15
