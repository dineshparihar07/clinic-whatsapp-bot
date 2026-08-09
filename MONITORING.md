# Monitoring & Alerting Guide

Production monitoring setup for the Clinic WhatsApp Bot.

## Built-in Monitoring

### Health Check Endpoint

```bash
curl https://your-app.com/health
```

Returns:
```json
{
  "status": "ok",
  "service": "Clinic WhatsApp Bot",
  "version": "0.1.0"
}
```

### Metrics Endpoint

```bash
curl https://your-app.com/api/metrics
```

Returns counters, timings, and last error:
```json
{
  "status": "ok",
  "metrics": {
    "counters": {
      "messages_received": 42,
      "appointments_booked": 15,
      "reminders_sent": 8
    },
    "timings": {
      "webhook_processing": {
        "count": 42,
        "min": 45,
        "max": 2341,
        "avg": 234
      }
    }
  },
  "last_error": "..."
}
```

### Admin Dashboard Endpoints

```bash
# Appointments
GET /api/admin/appointments?status=confirmed&from_date=2025-01-01

# Patients
GET /api/admin/patients

# Slots
GET /api/admin/slots?service=Dental&available_only=true

# Analytics
GET /api/admin/analytics/overview
GET /api/admin/analytics/appointments-by-service
GET /api/admin/analytics/daily-bookings?days=30
```

## Structured Logging

All logs are JSON formatted for easy parsing in ELK, Splunk, etc.

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "clinic_bot",
  "message": "Message received from +14155552671",
  "module": "webhook",
  "function": "handle_webhook",
  "line": 42,
  "event": "message_received",
  "phone_number": "+14155552671",
  "message_type": "text",
  "intent": "book"
}
```

### Enable JSON Logging

Set `ENV=production` in `.env`:

```bash
ENV=production
LOG_LEVEL=INFO
```

## Key Metrics to Monitor

### Message Processing
- `messages_received` — Total WhatsApp messages
- `webhook_processing_time_ms` — Time to process message
- `gemini_processing_time_ms` — AI inference latency
- `whatsapp_api_errors` — Failed WhatsApp API calls

### Appointments
- `appointments_booked` — Total bookings
- `appointments_cancelled` — Cancellations
- `appointment_confirmation_rate` — % confirmed after booking
- `double_booking_attempts` — Prevention check

### Reminders
- `reminders_24h_sent` — 24-hour reminders
- `reminders_2h_sent` — 2-hour reminders
- `reminder_send_failures` — Failed reminder sends

### Waiting List
- `waiting_list_entries` — Patients waiting
- `waiting_list_notified` — Offers sent
- `waiting_list_conversions` — Bookings from waitlist

### System Health
- `database_query_time_ms` — DB latency
- `api_response_time_ms` — API latency
- `error_rate` — % of failed requests
- `uptime` — Service availability

## Alerting Rules

### Critical Alerts

**1. High Error Rate**
- Trigger: > 5% of requests failing
- Action: Page oncall engineer
- Example: WhatsApp API down

**2. Database Connection Errors**
- Trigger: 3+ failed connections in 5 minutes
- Action: Check database service
- Restart connection pool

**3. Gemini API Errors**
- Trigger: 10+ API errors in 5 minutes
- Action: Check API quota/billing
- Enable fallback keyword matching

**4. Message Queue Backup**
- Trigger: > 100 unprocessed messages
- Action: Scale horizontally
- Check webhook latency

### Warning Alerts

**1. High Latency**
- Trigger: p95 response time > 5 seconds
- Action: Check database slow queries
- Review Gemini API performance

**2. Waiting List Growth**
- Trigger: > 50 new entries in 1 hour
- Action: Check slot availability
- Alert clinic to add slots

**3. Low Reminder Send Rate**
- Trigger: < 80% of reminders sent
- Action: Check WhatsApp template status
- Verify phone number ID

## Monitoring Setup

### Option 1: Render Dashboard (Included)

Render automatically captures:
- CPU usage
- Memory usage
- Request rates
- Error logs

Access via Render dashboard.

### Option 2: Datadog

```python
# Add to requirements.txt
datadog==0.46.0
```

```python
# In main.py
from datadog import initialize, api
from lib.monitoring import metrics

options = {
    'api_key': os.getenv('DATADOG_API_KEY'),
    'app_key': os.getenv('DATADOG_APP_KEY')
}
initialize(**options)

@app.on_event("startup")
async def startup_event():
    # Existing startup code...
    
    # Send initial metric
    api.Metric.send(
        metric="clinic_bot.startup",
        points=1,
        tags=["env:production"]
    )
```

### Option 3: New Relic

```python
# Add to requirements.txt
newrelic==8.10.0
```

```bash
# Start with APM agent
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program python main.py
```

### Option 4: Custom Monitoring

Use `/api/metrics` endpoint to build custom dashboard:

```javascript
// Example: Grafana dashboard queries
- Query: /api/admin/analytics/daily-bookings?days=30
- Query: /api/admin/appointments?status=confirmed
- Query: /api/metrics/counters
```

## Logging Pipeline

### Local Development

Logs to stdout (console):
```
2025-01-15 10:30:45,123 - clinic_bot - INFO - Message received from ...
```

### Production (Render)

Logs sent to Render's log viewer. Access via:
```bash
render logs your-app-name
```

### Production (Custom Stack)

Forward logs to external service:

```bash
# /etc/rsyslog.d/clinic-bot.conf
:programname, isequal, "clinic_bot" @@syslog.example.com:514
```

## Database Query Monitoring

Monitor slow queries:

```python
# In lib/db.py
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    if total_time > 1.0:  # Log queries > 1 second
        logger.warning(f"Slow query: {statement[:100]}... ({total_time:.2f}s)")
```

## Incident Response

### Message Processing Down
1. Check webhook URL is correct in Meta dashboard
2. Verify WHATSAPP_VERIFY_TOKEN matches
3. Check server logs for errors
4. Restart app (Render: push to main branch)

### Reminders Not Sending
1. Check WhatsApp token is valid
2. Verify phone number ID is correct
3. Check template approval status in Meta
4. Test with manual API call

### High Latency
1. Check database connection pool
2. Monitor Gemini API response times
3. Look for N+1 query problems
4. Consider caching

### Database Issues
1. Check connection string
2. Verify database is running
3. Check connection limits
4. Review slow query log

## Dashboards

### Sample Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Clinic WhatsApp Bot",
    "panels": [
      {
        "title": "Messages Processed",
        "targets": [
          {"expr": "clinic_bot_messages_received_total"}
        ]
      },
      {
        "title": "Appointments Booked",
        "targets": [
          {"expr": "clinic_bot_appointments_booked_total"}
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {"expr": "rate(clinic_bot_errors_total[5m])"}
        ]
      },
      {
        "title": "API Latency",
        "targets": [
          {"expr": "clinic_bot_api_latency_ms"}
        ]
      }
    ]
  }
}
```

## SLA Targets

| Metric | Target | Severity |
|--------|--------|----------|
| Uptime | 99.9% | Critical |
| Message Processing | < 5s p95 | High |
| Reminder Delivery | > 95% | High |
| Database Latency | < 500ms p99 | Medium |
| Error Rate | < 1% | Medium |

## Runbook

See [RUNBOOK.md](RUNBOOK.md) for incident procedures.

---

**Questions?** Check logs or contact team.
