# Production Deployment Checklist

Complete this checklist before deploying to production.

## Pre-Deployment (1 Week Before)

### 1. Environment & Credentials ✅
- [ ] WhatsApp Business Account created
- [ ] WhatsApp Cloud API enabled
- [ ] WhatsApp phone number registered
- [ ] WHATSAPP_TOKEN obtained
- [ ] WHATSAPP_PHONE_NUMBER_ID obtained
- [ ] WHATSAPP_VERIFY_TOKEN generated (random string)
- [ ] Gemini API key obtained from Google AI Studio
- [ ] Gemini API quota checked and sufficient

### 2. Database Setup ✅
- [ ] PostgreSQL database created (production grade)
- [ ] Database backups configured
- [ ] DATABASE_URL obtained
- [ ] Connection tested: `psql $DATABASE_URL -c "SELECT 1"`
- [ ] Schema initialized: `psql $DATABASE_URL < db/schema.sql`
- [ ] Sample slots seeded: `python scripts/seed_demo_data.py`

### 3. Code Preparation ✅
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code formatting: `black . && isort .`
- [ ] Linting clean: `flake8 . --max-line-length=100`
- [ ] No debug prints left in code
- [ ] Logging configured properly
- [ ] Error handling comprehensive

### 4. Security Review ✅
- [ ] No hardcoded secrets in code
- [ ] All credentials in environment variables
- [ ] CRON_SECRET is strong (32+ chars)
- [ ] WHATSAPP_VERIFY_TOKEN is strong
- [ ] No SQL injection vulnerabilities
- [ ] Input validation on all endpoints
- [ ] Rate limiting considered (add if needed)
- [ ] CORS properly configured
- [ ] HTTPS enforced (provider setting)

### 5. Documentation ✅
- [ ] README.md complete and accurate
- [ ] API.md up to date
- [ ] SETUP.md tested (follow it from scratch)
- [ ] DEPLOYMENT.md reviewed
- [ ] MONITORING.md reviewed
- [ ] RUNBOOK.md reviewed

---

## Deployment Day (Day 1)

### 1. Platform Setup (Choose One)

#### Option A: Render.com
- [ ] Account created at render.com
- [ ] New "Web Service" created
- [ ] GitHub repo connected
- [ ] Environment variables configured:
  ```
  DATABASE_URL
  WHATSAPP_TOKEN
  WHATSAPP_PHONE_NUMBER_ID
  WHATSAPP_VERIFY_TOKEN
  GEMINI_API_KEY
  CRON_SECRET
  ENV=production
  LOG_LEVEL=INFO
  PORT=10000
  ```
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] First deploy triggered
- [ ] App URL obtained (e.g., https://clinic-bot.onrender.com)

#### Option B: Railway.app
- [ ] Account created at railway.app
- [ ] New project created
- [ ] GitHub connected
- [ ] PostgreSQL plugin added
- [ ] Environment variables configured (same as Render)
- [ ] Deploy triggered
- [ ] App URL obtained

#### Option C: AWS Lambda
- [ ] AWS account ready
- [ ] Lambda function created
- [ ] API Gateway configured
- [ ] Environment variables set
- [ ] Database accessible from Lambda
- [ ] Deployment tested

### 2. Database Initialization
- [ ] Connect to production database
- [ ] Run schema initialization:
  ```bash
  psql $DATABASE_URL < db/schema.sql
  ```
- [ ] Verify tables created:
  ```sql
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema='public';
  ```
- [ ] Seed initial demo slots (optional):
  ```bash
  python scripts/seed_demo_data.py
  ```

### 3. Application Deployment
- [ ] Code pushed to main branch
- [ ] CI/CD pipeline triggered automatically
- [ ] Build logs checked for errors
- [ ] Deployment completed successfully
- [ ] App accessible at production URL

### 4. Health Verification
- [ ] Health check passes:
  ```bash
  curl https://clinic-bot.onrender.com/health
  # Should return: {"status": "ok", ...}
  ```
- [ ] Root endpoint works:
  ```bash
  curl https://clinic-bot.onrender.com/
  ```
- [ ] Metrics accessible:
  ```bash
  curl https://clinic-bot.onrender.com/api/metrics
  ```
- [ ] Admin endpoints work:
  ```bash
  curl https://clinic-bot.onrender.com/api/admin/slots
  ```

---

## WhatsApp Integration (Day 1-2)

### 1. Webhook Configuration
- [ ] Get production app URL:
  ```
  https://clinic-bot.onrender.com
  ```
- [ ] Go to Meta Business Suite → WhatsApp → Settings
- [ ] Configure Webhook:
  - Callback URL: `https://clinic-bot.onrender.com/api/webhook`
  - Verify Token: `{WHATSAPP_VERIFY_TOKEN}`
- [ ] Click "Verify and Save"
- [ ] Subscribe to "messages" webhook
- [ ] Subscribe to "message_status" webhook (optional)

### 2. Test Webhook
- [ ] Test verification:
  ```bash
  curl "https://clinic-bot.onrender.com/api/webhook?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=YOUR_TOKEN"
  # Should return: test123
  ```
- [ ] Send test message from WhatsApp
- [ ] Check logs for message received:
  ```bash
  render logs clinic-bot | grep "Message received"
  ```
- [ ] Verify bot replied

### 3. Test Booking Flow
- [ ] From WhatsApp: "I want to book a general checkup"
- [ ] Bot: Shows available slots as buttons
- [ ] Click a slot
- [ ] Bot: Confirms appointment with details
- [ ] Check admin: `GET /api/admin/appointments`
- [ ] Verify appointment exists

---

## Cron Jobs Setup (Day 2)

### Option 1: GitHub Actions (Recommended)

Create `.github/workflows/reminders.yml`:

```yaml
name: Send Reminders
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes

jobs:
  reminders:
    runs-on: ubuntu-latest
    steps:
      - name: Send appointment reminders
        run: |
          curl -X POST https://clinic-bot.onrender.com/api/cron/reminders \
            -H "Authorization: Bearer ${{ secrets.CRON_SECRET }}"
            
  backfill:
    runs-on: ubuntu-latest
    steps:
      - name: Process waiting list
        run: |
          curl -X POST https://clinic-bot.onrender.com/api/cron/backfill-waiting-list \
            -H "Authorization: Bearer ${{ secrets.CRON_SECRET }}"
```

- [ ] Create workflows directory
- [ ] Add reminders.yml
- [ ] Add CRON_SECRET to GitHub Secrets
- [ ] Test first run manually:
  ```bash
  curl -X POST https://clinic-bot.onrender.com/api/cron/reminders \
    -H "Authorization: Bearer $CRON_SECRET"
  ```
- [ ] Check logs for success

### Option 2: Render Cron (if supported)

- [ ] Check Render dashboard for cron job settings
- [ ] Configure cron endpoints
- [ ] Set schedule

### Option 3: External Service (EasyCron, CloudScheduler)

- [ ] Create account at easycron.com or similar
- [ ] Configure reminder job:
  ```
  URL: https://clinic-bot.onrender.com/api/cron/reminders
  Authorization: Bearer {CRON_SECRET}
  Schedule: */15 * * * *
  ```
- [ ] Configure waiting list job:
  ```
  URL: https://clinic-bot.onrender.com/api/cron/backfill-waiting-list
  Schedule: 0 * * * *
  ```

---

## Monitoring Setup (Day 2-3)

### 1. Logging
- [ ] Production logging enabled (ENV=production)
- [ ] Log level set to INFO
- [ ] JSON logs verified in Render dashboard

### 2. Metrics
- [ ] `/api/metrics` endpoint accessible
- [ ] Metrics being collected
- [ ] Dashboard created to monitor metrics

### 3. Alerting (Optional but Recommended)
- [ ] Error rate alert: > 5% requests failing
- [ ] Latency alert: > 5 seconds p95
- [ ] Database connection alert
- [ ] WhatsApp API error alert

### 4. Backups
- [ ] Database backups configured
- [ ] Backup retention set (7-30 days)
- [ ] Test restore procedure
- [ ] Backup schedule verified (daily)

---

## Post-Deployment (Day 3-7)

### 1. Production Testing
- [ ] Send 5 test messages from WhatsApp
- [ ] Verify all appointments created
- [ ] Test cancellation flow
- [ ] Test waiting list
- [ ] Verify reminders (wait 24h or manually trigger)
- [ ] Check analytics endpoint

### 2. Monitoring
- [ ] Check metrics daily: `/api/metrics`
- [ ] Monitor error logs
- [ ] Check message latency
- [ ] Verify database queries are fast
- [ ] Monitor API response times

### 3. Performance Baseline
- [ ] Record baseline metrics:
  - Avg response time: _____ ms
  - Error rate: _____ %
  - Messages/hour: _____
  - Database latency: _____ ms
- [ ] Set up alerts based on baselines

### 4. Documentation
- [ ] Update runbook with production URLs
- [ ] Document any environment-specific configs
- [ ] Create team dashboard access
- [ ] Share monitoring dashboard with team
- [ ] Schedule on-call rotation

---

## Ongoing (Weekly)

- [ ] Review error logs
- [ ] Check metrics trends
- [ ] Verify backups completed
- [ ] Test incident response procedures
- [ ] Update documentation if needed
- [ ] Performance review

---

## Ongoing (Monthly)

- [ ] Database optimization review
- [ ] Security audit
- [ ] Cost analysis
- [ ] Capacity planning
- [ ] Update dependencies (if security patches)
- [ ] Disaster recovery drill

---

## Rollback Plan

If production deployment fails:

### Immediate (First 5 minutes)
1. Revert commit: `git revert <commit>`
2. Push to main: `git push origin main`
3. Wait for auto-redeploy
4. Verify health: `curl https://clinic-bot.onrender.com/health`

### If database corrupted
1. Restore from latest backup
2. Contact database provider support
3. Notify clinic staff

### If WhatsApp webhook misconfigured
1. Revert webhook URL in Meta dashboard
2. Update and re-verify
3. Test with message

---

## Success Criteria

You're ready for production when:

- ✅ All health checks pass
- ✅ Webhook receives messages correctly
- ✅ Full booking flow works end-to-end
- ✅ Reminders send at correct times
- ✅ Admin dashboard fully functional
- ✅ Metrics/monitoring active
- ✅ Error rate < 1%
- ✅ Response time < 5s p95
- ✅ Backups configured and tested
- ✅ Team trained on runbook
- ✅ On-call rotation established

---

## Contacts & Resources

### WhatsApp Support
- Meta Business Suite: https://business.facebook.com
- WhatsApp API Docs: https://developers.facebook.com/docs/whatsapp/

### Database
- Neon: https://neon.tech (support@neon.tech)
- Supabase: https://supabase.com (support.supabase.io)

### Deployment Platforms
- Render: https://render.com (support@render.com)
- Railway: https://railway.app (support@railway.app)
- AWS: https://aws.amazon.com (AWS support)

### Gemini API
- Google AI Studio: https://aistudio.google.com
- Documentation: https://ai.google.dev

### Incident Response
- On-Call: [Slack channel]
- War Room: [Meeting link]
- Status Page: [Status page URL]

---

**Deployment Date: _______________**
**Deployed By: _______________**
**Verified By: _______________**
**Notes: _______________**

---

*Next Review Date: [30 days from now]*
