# Quick Start: Production Deployment

Deploy to production in **30 minutes**.

---

## Step 1: Gather Credentials (5 min)

You need:

### WhatsApp
- `WHATSAPP_TOKEN` → Meta Business Suite
- `WHATSAPP_PHONE_NUMBER_ID` → Meta Business Suite
- `WHATSAPP_VERIFY_TOKEN` → Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### Gemini API
- `GEMINI_API_KEY` → Google AI Studio (aistudio.google.com)

### Database
- `DATABASE_URL` → PostgreSQL connection string
  ```
  postgresql://user:password@host:5432/clinic_bot
  ```

### Security
- `CRON_SECRET` → Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### Environment
```
ENV=production
LOG_LEVEL=INFO
PORT=10000
```

---

## Step 2: Choose Platform (2 min)

### Recommended: Render.com
1. Sign up: https://render.com
2. Create Web Service
3. Connect GitHub repo
4. Set environment variables (from Step 1)
5. Deploy

**Done!** App runs at `https://your-app.onrender.com`

### Alternative: Railway.app
1. Sign up: https://railway.app
2. Create project
3. Add PostgreSQL
4. Connect GitHub
5. Set env vars
6. Deploy

### Alternative: AWS Lambda
See DEPLOYMENT.md for detailed setup.

---

## Step 3: Setup Database (5 min)

```bash
# Connect to production database
psql $DATABASE_URL

# Initialize schema
psql $DATABASE_URL < db/schema.sql

# Seed demo slots (optional)
python scripts/seed_demo_data.py
```

---

## Step 4: Configure WhatsApp Webhook (10 min)

1. Go to https://business.facebook.com
2. Select your app → WhatsApp
3. Go to Settings → Webhooks
4. Set Webhook URL:
   ```
   https://your-app.onrender.com/api/webhook
   ```
5. Set Verify Token:
   ```
   {Your WHATSAPP_VERIFY_TOKEN}
   ```
6. Click "Verify and Save"
7. Subscribe to "messages" event

### Test:
```bash
# Should return your verify token
curl "https://your-app.onrender.com/api/webhook?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=YOUR_TOKEN"
```

---

## Step 5: Test Booking Flow (5 min)

1. Send WhatsApp message:
   ```
   I want to book a general checkup appointment
   ```

2. Bot should respond with available slots

3. Click a slot

4. Bot confirms appointment

5. Verify in admin:
   ```bash
   curl https://your-app.onrender.com/api/admin/appointments
   ```

---

## Step 6: Setup Reminders (3 min)

### Option A: GitHub Actions (Easiest)

Create `.github/workflows/reminders.yml`:

```yaml
name: Reminders
on:
  schedule:
    - cron: '*/15 * * * *'

jobs:
  reminders:
    runs-on: ubuntu-latest
    steps:
      - run: curl -X POST https://your-app.onrender.com/api/cron/reminders \
              -H "Authorization: Bearer ${{ secrets.CRON_SECRET }}"
  
  waiting:
    runs-on: ubuntu-latest
    steps:
      - run: curl -X POST https://your-app.onrender.com/api/cron/backfill-waiting-list \
              -H "Authorization: Bearer ${{ secrets.CRON_SECRET }}"
```

Then add `CRON_SECRET` to GitHub Secrets.

### Option B: Manual Test

```bash
curl -X POST https://your-app.onrender.com/api/cron/reminders \
  -H "Authorization: Bearer $CRON_SECRET"
```

---

## Step 7: Verify Production (Final check)

```bash
# Health check
curl https://your-app.onrender.com/health

# Metrics
curl https://your-app.onrender.com/api/metrics | jq .

# Admin dashboard
curl https://your-app.onrender.com/api/admin/appointments

# Analytics
curl https://your-app.onrender.com/api/admin/analytics/overview
```

All should return 200 OK.

---

## Done! 🎉

Your production bot is live!

### Next Steps

1. **Share WhatsApp number** with clinic staff
2. **Monitor** metrics dashboard daily
3. **Test** booking flow with real patients
4. **Configure** alerts (see MONITORING.md)
5. **Schedule** on-call rotation
6. **Document** any custom changes

---

## Troubleshooting

### Bot not receiving messages?
- Check webhook URL in Meta dashboard
- Check `WHATSAPP_VERIFY_TOKEN` matches
- Check logs: `render logs clinic-bot`

### Database connection error?
- Verify `DATABASE_URL` is correct
- Test: `psql $DATABASE_URL -c "SELECT 1"`
- Check firewall rules

### Gemini errors?
- Verify API key in Google Cloud console
- Check quota limits
- Test: `python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY')"`

### Reminders not sending?
- Check `WHATSAPP_TOKEN` is valid
- Verify `WHATSAPP_PHONE_NUMBER_ID` is correct
- Check template approval in Meta
- Test manually: `curl -X POST https://your-app.onrender.com/api/cron/reminders ...`

---

## Monitoring Checklist

Daily:
- [ ] Check error rate: `/api/metrics`
- [ ] Review logs
- [ ] Verify message processing

Weekly:
- [ ] Review trends in analytics
- [ ] Check database performance
- [ ] Verify backups completed

Monthly:
- [ ] Capacity planning
- [ ] Security audit
- [ ] Update dependencies

---

## Support

See these docs for help:

- **Setup Issues** → SETUP.md
- **API Reference** → API.md
- **Deployment Details** → DEPLOYMENT.md
- **Incidents** → RUNBOOK.md
- **Monitoring** → MONITORING.md
- **Full Checklist** → PRODUCTION_CHECKLIST.md

---

**You're ready! Deploy and enjoy your WhatsApp bot 🚀**
