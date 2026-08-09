# Setup Guide

Complete setup instructions for the Clinic WhatsApp Bot.

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- WhatsApp Business Account with Cloud API access
- Google Gemini API key
- Git

## Step 1: Clone & Install

```bash
git clone https://github.com/dineshparihar07/clinic-whatsapp-bot.git
cd clinic-whatsapp-bot

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

### WhatsApp Setup
1. Go to [Meta Business Suite](https://business.facebook.com)
2. Create Business Account (if needed)
3. Go to Apps → Create App → Business
4. Add WhatsApp product
5. In WhatsApp Settings:
   - Get your **Phone Number ID** → `WHATSAPP_PHONE_NUMBER_ID`
   - Get **Access Token** → `WHATSAPP_TOKEN`
   - Create verify token (any string) → `WHATSAPP_VERIFY_TOKEN`

### Gemini API Setup
1. Go to [Google AI Studio](https://aistudio.google.com)
2. Click "Get API Key"
3. Copy key → `GEMINI_API_KEY`

### Database Setup
1. Create PostgreSQL database:
   ```bash
   createdb clinic_bot
   ```
2. Get connection string:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/clinic_bot
   ```

### Cron Security
Generate a random secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Use this for `CRON_SECRET`

## Step 3: Initialize Database

```bash
python scripts/seed_demo_data.py
```

This creates:
- Demo slots for 30 days
- Sample patient records
- Tables for appointments, waiting lists, etc.

## Step 4: Run Locally

```bash
python main.py
```

Server runs at `http://localhost:3000`

Test it:
```bash
curl http://localhost:3000/health
```

## Step 5: Test Webhook

### Local Testing with ngrok

```bash
# In another terminal, start ngrok
ngrok http 3000

# Note the HTTPS URL (e.g., https://xxxx-xx-xxx-xxx-xx.ngrok.io)
```

### Configure WhatsApp Webhook

1. Go to Meta Business Suite → WhatsApp Settings
2. Under "Webhooks":
   - **Callback URL**: `https://xxxx-xx-xxx-xxx-xx.ngrok.io/api/webhook`
   - **Verify Token**: (use your `WHATSAPP_VERIFY_TOKEN`)
3. Click "Verify and Save"
4. Subscribe to `messages` webhook

### Test with Demo Message

Send a WhatsApp message to your number from one of the demo phones:
```
+1 (415) 555-2671
```

Try: "I want to book a general checkup appointment"

## Step 6: Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment to:
- Render.com (recommended)
- Railway.app
- AWS Lambda
- Heroku

## Troubleshooting

### "Database connection failed"
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check DATABASE_URL is correct in .env
```

### "Webhook verification failed"
- Ensure `WHATSAPP_VERIFY_TOKEN` matches in both .env and Meta dashboard
- Public URL must be HTTPS (not HTTP)
- Server must be running

### "No available slots"
```bash
# Reseed demo data
python scripts/seed_demo_data.py
```

### "Gemini API error"
- Check `GEMINI_API_KEY` is valid
- Verify API is enabled in Google Console
- Check quota/billing

### "WhatsApp token invalid"
- Generate new token in Meta Business Suite
- Token expires after 60 days
- Check token doesn't have leading/trailing spaces in .env

## Development

### Code Quality
```bash
# Format code
black . && isort .

# Lint
flake8 . --max-line-length=100

# Type checking
mypy lib/ api/
```

### Run Tests
```bash
pytest tests/ -v
```

### Database Migrations
For production changes to schema:
```bash
# Using Alembic (optional setup)
alembic init migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Monitoring

Check logs:
```bash
# Render
render logs your-app-name

# Railway
railway logs

# Local
python main.py (with logging output)
```

Monitor endpoints:
- `GET /health` → Server health
- `GET /` → API info
- `POST /api/webhook` → Message handling
- `POST /api/cron/reminders` → Reminder scheduling
- `POST /api/cron/backfill-waiting-list` → Waiting list processing

## Next Steps

1. ✅ Complete setup
2. ✅ Test locally
3. ✅ Deploy to production
4. ✅ Connect real WhatsApp Business Account
5. ✅ Configure reminders cron job
6. ✅ Monitor and iterate

---

**Need help?** Check:
- [README.md](README.md) for overview
- [DEPLOYMENT.md](DEPLOYMENT.md) for production
- [PROJECT_PLAN.md](PROJECT_PLAN.md) for architecture
