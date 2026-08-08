# Deployment Guide

This project is now built entirely in **Python** using **FastAPI**.

## Local Development

### 1. Setup Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Initialize Database
```bash
# Create tables using schema.sql
psql $DATABASE_URL < db/schema.sql

# Or use SQLAlchemy (auto-creates tables on startup)
python main.py
```

### 4. Run Development Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

Server runs at `http://localhost:3000`

---

## Production Deployment

### Option 1: Render.com (Recommended - easiest for Python)

1. **Connect GitHub repo to Render**
   - Go to [render.com](https://render.com)
   - Create new "Web Service"
   - Connect your GitHub repo

2. **Configure in Render Dashboard:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables:** Set all vars from `.env`
   - **Database:** Connect PostgreSQL (Neon or Render Postgres)

3. **Set Webhook URL in WhatsApp:**
   ```
   https://your-render-app.onrender.com/api/webhook
   ```

### Option 2: Railway.app

1. **Connect GitHub repo**
2. **Add PostgreSQL plugin**
3. **Set environment variables**
4. Deploy automatically

### Option 3: AWS Lambda + API Gateway (Serverless)

Use `serverless-python-requirements` plugin:
```bash
npm install -g serverless
serverless plugin install -n serverless-python-requirements
serverless deploy
```

### Option 4: Heroku (Deprecated but works)

```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

---

## Database Setup

### Using Neon (Recommended)
1. Go to [neon.tech](https://neon.tech)
2. Create PostgreSQL database
3. Copy connection string to `DATABASE_URL`

### Using Supabase
1. Go to [supabase.com](https://supabase.com)
2. Create project
3. Use the connection string from dashboard

---

## Cron Jobs

### Render.com Setup
Add cron job in your service dashboard or use GitHub Actions:

```yaml
# .github/workflows/reminders.yml
name: Send Reminders
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes

jobs:
  reminders:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger reminders
        run: |
          curl -X POST https://your-render-app.onrender.com/api/cron/reminders
```

---

## Monitoring & Logging

Check logs on deployment platform or use:
```bash
# Render
render logs your-app-name

# Railway
railway logs

# Heroku
heroku logs --tail
```

---

## Next Steps

1. ✅ Configure WhatsApp Business Account
2. ✅ Get Gemini API key
3. ✅ Set up PostgreSQL database
4. ✅ Deploy to Render/Railway/Lambda
5. ✅ Test webhook with WhatsApp
