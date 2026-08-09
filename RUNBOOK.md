# Incident Runbook

Procedures for responding to common incidents.

## 1. Service Down / 503 Errors

### Check
```bash
# Check service status
curl https://your-app.com/health

# Check logs
render logs your-app-name

# Check database connectivity
psql $DATABASE_URL -c "SELECT 1"
```

### Fix
**If app not responding:**
1. SSH into server or use provider dashboard
2. Restart app: `systemctl restart clinic-bot`
3. For Render: Push code change or redeploy

**If database unreachable:**
1. Check DATABASE_URL in .env
2. Verify database is running
3. Check firewall rules
4. Increase connection pool if needed

**If all services up but still 503:**
1. Check logs for stack trace
2. Look for OOM (out of memory) errors
3. Scale up resources (Render settings)
4. Check disk space

---

## 2. Messages Not Being Received

### Symptoms
- Patient messages don't trigger replies
- No new appointments being created
- Webhook logs are empty

### Check
```bash
# Verify webhook URL is configured
# In Meta Business Suite → WhatsApp Settings → Webhooks
# Should be: https://your-app.com/api/webhook

# Test webhook manually
curl -X GET "https://your-app.com/api/webhook?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=YOUR_TOKEN"

# Should return: test123
```

### Fix
**If webhook URL is wrong:**
1. Update in Meta dashboard
2. Wait 5 minutes for cache clear
3. Test with patient message

**If verify token mismatch:**
1. Check WHATSAPP_VERIFY_TOKEN in .env
2. Must match exactly in Meta dashboard
3. Redeploy after fixing

**If webhook not receiving messages:**
1. Check webhook subscriptions in Meta
2. Must have "messages" selected
3. Re-subscribe if needed

---

## 3. Reminders Not Sending

### Symptoms
- Patients don't receive 24h/2h reminders
- Cron logs show success but no WhatsApp API calls

### Check
```bash
# Check reminder job ran
render logs your-app-name | grep "reminders"

# Test manually
curl -X POST https://your-app.com/api/cron/reminders \
  -H "Authorization: Bearer $CRON_SECRET"

# Check WhatsApp token validity
# In Meta dashboard → Settings → Access Tokens
```

### Fix
**If token expired:**
1. Generate new token in Meta dashboard
2. Update WHATSAPP_TOKEN in .env
3. Redeploy
4. Re-run reminders

**If template not approved:**
1. Go to Meta Dashboard → WhatsApp
2. Check template approval status
3. Resubmit if rejected
4. Use fallback text messages (already supported)

**If rate limited:**
1. Check WhatsApp throughput limits
2. Space out reminder sends
3. Queue messages if needed
4. Contact Meta support for higher limit

---

## 4. High Latency / Slow Responses

### Symptoms
- Responses take > 5 seconds
- Database timeouts in logs
- Gemini API timeouts

### Check
```bash
# Check metrics
curl https://your-app.com/api/metrics

# Check database connection pool
# Look for: "connect_timeout" errors

# Monitor with:
watch -n 1 'curl -s https://your-app.com/api/metrics | jq .metrics.timings'
```

### Fix
**If database slow:**
1. Run query analysis:
   ```sql
   SELECT query, calls, total_time FROM pg_stat_statements
   ORDER BY total_time DESC LIMIT 10;
   ```
2. Add missing indexes
3. Increase connection pool:
   ```python
   # In lib/db.py
   engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)
   ```
4. Scale up database (add CPU/RAM)

**If Gemini slow:**
1. Check response times in logs
2. Google API quota issue?
3. Try reducing prompt size
4. Add caching for common queries

**If general API slow:**
1. Check CPU usage (Render dashboard)
2. Scale up instance size
3. Profile code with py-spy
4. Look for N+1 query patterns

---

## 5. Database Connection Pool Exhausted

### Symptoms
```
sqlalchemy.pool.QueuePool: QueuePool limit of size 5 overflow 10 reached
```

### Fix
```python
# In lib/db.py, increase pool size:
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

Then redeploy.

---

## 6. Memory Leak / OOM

### Symptoms
- Memory usage increases over time
- App crashes with OOM error
- Swap usage high

### Check
```bash
# Monitor memory in real-time
watch -n 1 'ps aux | grep python'

# Check for leaked connections
curl https://your-app.com/api/metrics | jq '.metrics.counters'
```

### Fix
1. Check for unclosed database sessions:
   ```python
   # Make sure all sessions close properly
   db.close()  # In finally blocks
   ```

2. Monitor async task queue:
   ```python
   # Verify background tasks complete
   ```

3. Restart app (will reclaim memory):
   - Render: Push new commit or manual redeploy
   - AWS Lambda: Auto-recycles on deployment

---

## 7. WhatsApp API Errors

### Common Errors

**"Invalid phone number"**
- Verify phone format is E.164: `+1234567890`
- Check phone is registered with WhatsApp

**"Message template not found"**
- Template name must match exactly in Meta
- Check template approval status
- Use fallback text messages

**"Rate limit exceeded"**
- Slow down message send rate
- Queue messages in database
- Contact Meta for higher limit

**"Invalid access token"**
- Generate new token in Meta dashboard
- Token expires after 60 days
- Check no leading/trailing whitespace

### Debug
```python
# In lib/whatsapp.py, add detailed logging:
if response.status_code >= 400:
    logger.error(f"WhatsApp error: {response.json()}")
```

---

## 8. Gemini AI Errors

### Common Errors

**"API key invalid"**
- Check GEMINI_API_KEY in .env
- Test in Google AI Studio
- Regenerate if needed

**"Quota exceeded"**
- Check billing in Google Cloud
- Upgrade tier if needed
- Implement request caching

**"No candidates returned"**
- Model returned empty response
- Fallback to keyword classification

### Workaround
```python
# In lib/gemini.py, add fallback:
try:
    parsed = parse_intent(user_message)
except Exception:
    # Fallback to keyword matching
    parsed = fallback_classify(user_message)
```

---

## 9. Double Booking Detected

### Immediate Action
1. Identify affected appointment ID
2. Check if both patients confirmed
3. Contact patient with lower booking time
4. Offer alternative slot or reschedule

### Prevention
- Already implemented in code
- Verify slot.is_available before booking
- Use database transaction locks

### Debug
```sql
-- Find double-booked slots
SELECT slot_id, COUNT(*) as count
FROM appointments
WHERE status IN ('booked', 'confirmed')
GROUP BY slot_id
HAVING COUNT(*) > 1;
```

---

## 10. Waiting List Issues

### Symptoms
- Waiting patients not notified when slots free
- Waiting list entries not expiring

### Check
```bash
# Check waiting list status
curl https://your-app.com/api/admin/waiting-list

# Check last backfill job
render logs your-app-name | grep backfill
```

### Fix
1. Manually trigger backfill:
   ```bash
   curl -X POST https://your-app.com/api/cron/backfill-waiting-list \
     -H "Authorization: Bearer $CRON_SECRET"
   ```

2. Check job scheduling:
   - GitHub Actions YAML configured?
   - Cron syntax correct?
   - Job logs show execution?

---

## Escalation Path

1. **Tier 1 (Monitoring Alerts)**
   - Automated health checks
   - Restart app if down
   - Check logs

2. **Tier 2 (On-Call Engineer)**
   - Page if not resolved in 5 minutes
   - SSH into server
   - Check database
   - Review code changes

3. **Tier 3 (Team)**
   - Major outage > 15 minutes
   - Database corruption
   - Security incident
   - Call emergency meeting

---

## Prevention

### Daily
- Monitor `/api/metrics` for anomalies
- Check error logs
- Verify reminder sends completed

### Weekly
- Run performance analysis
- Review slow queries
- Check disk space

### Monthly
- Review incident logs
- Update runbook
- Capacity planning
- Security audit

---

## Contact

- **On-Call:** [Slack channel]
- **Database:** [Database provider support]
- **WhatsApp:** Meta Business Support
- **Gemini:** Google Cloud Support

---

**Last Updated:** 2025-01-15
**Next Review:** 2025-02-15
