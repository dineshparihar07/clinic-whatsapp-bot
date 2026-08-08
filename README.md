# Clinic WhatsApp Appointment Bot

An automated appointment booking system for clinics using WhatsApp, powered by Python.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI |
| Server | Uvicorn |
| Database | PostgreSQL with SQLAlchemy ORM |
| AI/NLU | Google Gemini API |
| Chat Channel | WhatsApp Business Cloud API (Meta) |
| Hosting | Render.com, Railway.app, or AWS Lambda |
| Scheduling | APScheduler (built-in) or GitHub Actions |

## Features

- 💬 **WhatsApp Integration** — Patients book appointments via WhatsApp
- 🤖 **AI-Powered** — Gemini API understands appointment requests naturally
- 📅 **Slot Management** — Automatic availability checking and booking
- 🔔 **Smart Reminders** — Automated reminders 24h and 2h before appointments
- ⏳ **Waiting List** — Backfill cancelled slots with waiting patients
- 🔐 **Secure** — Webhook verification, secure token handling

## Project Structure

```
.
├── main.py                 # FastAPI app entry point
├── api/
│   ├── webhook.py         # WhatsApp webhook handler
│   └── cron.py            # Scheduled jobs (reminders, backfill)
├── lib/
│   ├── db.py              # SQLAlchemy models & database
│   ├── whatsapp.py        # WhatsApp API client
│   └── gemini.py          # Gemini AI integration
├── db/
│   └── schema.sql         # Database schema
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── Procfile               # Deployment configuration
└── PROJECT_PLAN.md        # Full project specification
```

## Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/dineshparihar07/clinic-whatsapp-bot.git
cd clinic-whatsapp-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with:
# - WHATSAPP_TOKEN (from Meta Business Account)
# - GEMINI_API_KEY (from Google AI Studio)
# - DATABASE_URL (PostgreSQL connection string)
```

### 3. Initialize Database
```bash
# Using PostgreSQL client
psql $DATABASE_URL < db/schema.sql
```

### 4. Run Development Server
```bash
uvicorn main:app --reload --port 3000
```

Server runs at `http://localhost:3000`

### 5. Test Webhook
```bash
# Verify endpoint
curl http://localhost:3000/health

# Test webhook verification
curl "http://localhost:3000/api/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to:
- **Render.com** (easiest)
- **Railway.app**
- **AWS Lambda**
- **Heroku**

Quick Render deployment:
```bash
# Push to GitHub, connect repo to Render.com
# Set environment variables in dashboard
# Render auto-deploys on git push
```

## API Endpoints

### Webhook
- `GET /api/webhook` — WhatsApp verification handshake
- `POST /api/webhook` — Receive messages & handle bookings

### Scheduled Jobs (Cron)
- `POST /api/cron/reminders` — Send appointment reminders
- `POST /api/cron/backfill-waiting-list` — Notify waiting patients

### Health Check
- `GET /health` — Service status

## Database Schema

**Tables:**
- `patients` — Patient info (phone, name)
- `slots` — Available appointment slots
- `appointments` — Bookings (patient + slot + status)
- `waiting_list` — Patients waiting for slots
- `conversation_state` — Multi-turn conversation tracking

See `db/schema.sql` for full schema.

## Environment Variables

```env
WHATSAPP_TOKEN=your_business_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=webhook_verification_token
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://user:pass@host/dbname
PORT=3000
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black . && isort . && flake8 .
```

### Database Migrations
```bash
# Using Alembic (if needed)
alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Troubleshooting

### Webhook not receiving messages
1. Verify `WHATSAPP_VERIFY_TOKEN` matches WhatsApp dashboard
2. Check webhook URL is publicly accessible
3. Confirm "Webhook Subscriptions" include `messages` in dashboard

### Database connection errors
1. Test connection string: `psql $DATABASE_URL`
2. Verify database exists and user has permissions
3. Check firewall/network rules

### Gemini API errors
1. Verify API key is correct
2. Check quota limits in Google Cloud console
3. Ensure API is enabled

## Project Phases

See `PROJECT_PLAN.md` for full development roadmap:
1. ✅ Python stack setup
2. ⏳ WhatsApp webhook integration
3. ⏳ Gemini AI layer
4. ⏳ Slot & booking logic
5. ⏳ Confirmation system
6. ⏳ Reminder system
7. ⏳ Confirm/cancel handling
8. ⏳ Waiting list backfill
9. ⏳ Testing & QA
10. ⏳ Production launch

## Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License — see LICENSE file

## Support

For issues or questions:
- 📧 Email: support@clinic-bot.dev
- 🐛 GitHub Issues: [Report a bug](https://github.com/dineshparihar07/clinic-whatsapp-bot/issues)
- 💬 Discussions: [Ask a question](https://github.com/dineshparihar07/clinic-whatsapp-bot/discussions)

---

**Built with ❤️ using Python & FastAPI**
