# Incident Response Runbook

This document provides step-by-step procedures for responding to production incidents in the Diamond Lens MLB Stats Assistant.

## Table of Contents

1. [Incident Severity Levels](#incident-severity-levels)
2. [Alert Response Procedures](#alert-response-procedures)
3. [Common Incidents and Solutions](#common-incidents-and-solutions)
4. [Escalation Procedures](#escalation-procedures)
5. [Post-Incident Review](#post-incident-review)

---

## Incident Severity Levels

### SEV-1: Critical (Complete Service Outage)

**Definition**: Application completely unavailable or major data loss

**Examples**:
- Backend API returning 500 errors for all requests
- Frontend not loading
- Database connection completely lost
- Data corruption detected

**Response time**: Immediate (< 5 minutes)

**Resolution target**: < 1 hour

**Actions**:
- Page on-call engineer immediately
- Create incident channel (Slack/Teams)
- Executive notification required
- Public status page update

---

### SEV-2: High (Partial Service Degradation)

**Definition**: Significant degradation affecting multiple users

**Examples**:
- API latency > 10 seconds (p95)
- Error rate > 5%
- Specific query types failing (e.g., all batting splits queries)
- BigQuery quota exceeded

**Response time**: < 15 minutes

**Resolution target**: < 4 hours

**Actions**:
- Notify on-call engineer
- Begin investigation
- Internal stakeholder notification

---

### SEV-3: Medium (Minor Degradation)

**Definition**: Limited impact on subset of users

**Examples**:
- Specific player queries failing
- Chart rendering issues
- Slow response times for certain query types
- High memory usage (80-90%)

**Response time**: < 1 hour

**Resolution target**: < 24 hours

**Actions**:
- Create ticket
- Investigate during business hours
- Monitor for escalation

---

### SEV-4: Low (Cosmetic or Non-Functional)

**Definition**: No user impact but operational concern

**Examples**:
- Logging errors
- Monitoring gaps
- Documentation outdated
- Non-critical dependency vulnerabilities

**Response time**: < 1 business day

**Resolution target**: < 1 week

---

## Alert Response Procedures

### Alert: Backend API Down

**Trigger**: Uptime check fails for 60 seconds

**Severity**: SEV-1

#### Investigation Steps

1. **Verify the alert** (1 min)
   ```bash
   # Check if backend is responding
   curl https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/health
   ```

2. **Check Cloud Run service status** (2 min)
   ```bash
   # View service status
   gcloud run services describe mlb-diamond-lens-api --region=asia-northeast1

   # Check recent revisions
   gcloud run revisions list --service=mlb-diamond-lens-api --region=asia-northeast1
   ```

3. **Review recent logs** (3 min)
   ```bash
   # Check for errors in last 10 minutes
   gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
     --limit 50 \
     --format json \
     --freshness=10m
   ```

#### Common Causes and Solutions

**Cause 1: Out of Memory (OOMKilled)**

**Symptoms**: Logs show "Memory limit exceeded" or container restarts

**Solution**:
```bash
# Increase memory allocation
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --memory=1Gi

# Or via Terraform
# Update terraform/modules/cloud-run/main.tf: memory = "1Gi"
terraform apply
```

**Cause 2: Dependency Failure (BigQuery/Gemini API)**

**Symptoms**: Logs show connection errors or API timeouts

**Solution**:
```bash
# Check service account permissions
gcloud projects get-iam-policy tksm-dash-test-25 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:907924272679-compute@developer.gserviceaccount.com"

# Verify Gemini API key
gcloud secrets versions access latest --secret="GEMINI_API_KEY"

# Test BigQuery access
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `tksm-dash-test-25.mlb_analytics_dash_25.fact_batting_stats_with_risp`'
```

**Cause 3: Bad Deployment**

**Symptoms**: Issue started immediately after deployment

**Solution**:
```bash
# Rollback to previous revision
gcloud run services update-traffic mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --to-revisions=PREVIOUS_REVISION=100

# Or redeploy last known good image
gcloud run deploy mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --image=gcr.io/tksm-dash-test-25/mlb-diamond-lens-api:PREVIOUS_TAG
```

---

### Alert: Frontend Down

**Trigger**: Frontend uptime check fails for 60 seconds

**Severity**: SEV-1

#### Investigation Steps

1. **Verify frontend accessibility**
   ```bash
   curl https://mlb-diamond-lens-frontend-907924272679.asia-northeast1.run.app/
   ```

2. **Check Cloud Run service**
   ```bash
   gcloud run services describe mlb-diamond-lens-frontend --region=asia-northeast1
   ```

3. **Check nginx logs**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mlb-diamond-lens-frontend" \
     --limit 50 \
     --freshness=10m
   ```

#### Solutions

**Cause: Backend URL misconfiguration**

**Symptoms**: Frontend loads but API calls fail

**Solution**:
```bash
# Verify VITE_API_URL environment variable
gcloud run services describe mlb-diamond-lens-frontend \
  --region=asia-northeast1 \
  --format="value(spec.template.spec.containers[0].env)"

# Update if incorrect
gcloud run services update mlb-diamond-lens-frontend \
  --region=asia-northeast1 \
  --set-env-vars="VITE_API_URL=https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app"
```

---

### Alert: High Memory Usage (>80%)

**Trigger**: Cloud Run memory exceeds 80% for 5 minutes

**Severity**: SEV-2

#### Investigation Steps

1. **Check current memory usage**
   ```bash
   # Cloud Monitoring query
   gcloud monitoring time-series list \
     --filter='metric.type="run.googleapis.com/container/memory/utilizations"' \
     --format=json
   ```

2. **Identify memory-intensive operations**
   ```bash
   # Check for large result sets in logs
   gcloud logging read "jsonPayload.query_type=* AND resource.type=cloud_run_revision" \
     --limit 50 \
     --format json
   ```

#### Solutions

**Short-term mitigation**:
```bash
# Increase memory allocation
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --memory=1Gi
```

**Long-term fix**:
- Implement result pagination for large BigQuery queries
- Add query result caching
- Optimize DataFrame operations in Python

---

### Alert: High CPU Usage (>80%)

**Trigger**: Cloud Run CPU exceeds 80% for 5 minutes

**Severity**: SEV-2

#### Investigation Steps

1. **Check concurrent request count**
   ```bash
   # View active instances
   gcloud run services describe mlb-diamond-lens-api \
     --region=asia-northeast1 \
     --format="value(status.traffic[0].latestRevision)"
   ```

2. **Review slow queries**
   ```bash
   # Find high latency requests
   gcloud logging read "jsonPayload.latency_ms>5000" \
     --limit 50 \
     --format json
   ```

#### Solutions

**Short-term**:
```bash
# Increase max instances
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --max-instances=50
```

**Long-term**:
- Optimize BigQuery queries (add indexes, reduce full table scans)
- Implement query result caching
- Add rate limiting for expensive operations

---

### Alert: High Error Rate (>1%)

**Trigger**: Error rate exceeds 1% for 10 minutes

**Severity**: SEV-2

#### Investigation Steps

1. **Identify error types**
   ```bash
   # Group errors by type
   gcloud logging read "jsonPayload.error_type=* AND severity=ERROR" \
     --limit 100 \
     --format json | jq '.[] | .jsonPayload.error_type' | sort | uniq -c
   ```

2. **Review error details**
   ```bash
   # Get recent error messages
   gcloud logging read "jsonPayload.error_type=bigquery_error" \
     --limit 10 \
     --format="table(timestamp, jsonPayload.error_message)"
   ```

#### Solutions by Error Type

**bigquery_error**:
- Check BigQuery quota: Cloud Console → BigQuery → Quotas
- Verify table existence and permissions
- Run schema validation: `python backend/scripts/validate_schema_config.py`

**llm_error**:
- Verify Gemini API key validity
- Check Gemini API quota and rate limits
- Review recent Gemini API model updates

**null_response**:
- Check application logs for logic errors
- Verify data exists for the query parameters
- Review recent code changes in `ai_service.py`

---

## Escalation Procedures

### Level 1: On-Call Engineer

**Responsibilities**:
- Initial triage and investigation
- Execute runbook procedures
- Implement immediate mitigations

**Escalate to Level 2 if**:
- Unable to resolve within 30 minutes (SEV-1)
- Requires infrastructure changes beyond Cloud Run
- Needs access to restricted resources

---

### Level 2: Senior Engineer / Tech Lead

**Responsibilities**:
- Complex debugging and root cause analysis
- Architecture decisions for mitigation
- Coordinate with external teams (GCP Support)

**Escalate to Level 3 if**:
- GCP platform issue suspected
- Security incident detected
- Multiple services affected

---

### Level 3: Engineering Manager / CTO

**Responsibilities**:
- Executive decision-making
- Customer communication
- GCP Support escalation
- Post-incident review oversight

---

## Incident Communication

### Internal Communication Template

```
[INCIDENT] [SEV-X] Brief description

Status: INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED
Started: YYYY-MM-DD HH:MM UTC
Impact: Description of user impact
ETA: Estimated time to resolution

Current Actions:
- Action 1
- Action 2

Next Update: In X minutes
```

### Status Page Update Template

```
We are currently investigating issues with the Diamond Lens application.
Users may experience [describe impact].

We will provide updates every 30 minutes.

Last updated: YYYY-MM-DD HH:MM UTC
```

---

## Post-Incident Review

### Timeline

**Within 24 hours**: Initial incident summary

**Within 3 business days**: Full post-mortem document

**Within 1 week**: Action items assigned and tracked

---

### Post-Mortem Template

```markdown
# Incident Post-Mortem: [Brief Description]

## Incident Summary
- **Date**: YYYY-MM-DD
- **Duration**: X hours Y minutes
- **Severity**: SEV-X
- **Impact**: X users affected, Y requests failed

## Timeline (UTC)
- HH:MM - Incident started
- HH:MM - Alert triggered
- HH:MM - Investigation began
- HH:MM - Root cause identified
- HH:MM - Mitigation applied
- HH:MM - Service restored
- HH:MM - Monitoring confirmed normal operation

## Root Cause
Detailed explanation of what went wrong and why.

## Impact Assessment
- Requests failed: X
- Users affected: Y
- SLO impact: Z minutes of error budget consumed
- Revenue impact (if applicable): $X

## What Went Well
- Positive aspects of incident response
- Effective runbook procedures
- Good communication

## What Went Wrong
- Gaps in monitoring
- Delayed detection
- Insufficient documentation

## Action Items
| Action | Owner | Priority | Due Date | Status |
|--------|-------|----------|----------|--------|
| Add monitoring for X | Engineer A | High | YYYY-MM-DD | Open |
| Update runbook | Engineer B | Medium | YYYY-MM-DD | Open |
| Implement circuit breaker | Engineer C | High | YYYY-MM-DD | Open |

## Lessons Learned
Key takeaways and systemic improvements needed.
```

---

## Emergency Contacts

### On-Call Rotation

Managed via PagerDuty / Opsgenie

**Escalation chain**:
1. On-call engineer (0-30 min)
2. Tech lead (30-60 min)
3. Engineering manager (60+ min)

### External Support

**Google Cloud Support**:
- Console: https://console.cloud.google.com/support
- Phone: [Support number based on support tier]
- Priority: P1 for SEV-1 incidents

**Gemini API Support**:
- Documentation: https://ai.google.dev/docs
- Community: https://discuss.ai.google.dev

---

## Useful Commands Reference

### Quick Diagnostics
```bash
# Check all services health
gcloud run services list --region=asia-northeast1

# View recent deployments
gcloud run revisions list --service=mlb-diamond-lens-api --region=asia-northeast1 --limit=5

# Check error logs (last 1 hour)
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --freshness=1h \
  --limit=50

# View custom metrics
gcloud monitoring time-series list \
  --filter='metric.type=starts_with("custom.googleapis.com/diamond-lens")'

# Check BigQuery quota
gcloud alpha bq show --project_id=tksm-dash-test-25

# Test backend locally
curl -X POST https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/api/v1/qa/player-stats \
  -H "Content-Type: application/json" \
  -d '{"query": "大谷翔平の2024年の打率は？", "season": 2024}'
```

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-01-15 | 1.0 | Initial runbook creation | - |

---

## References

- [SLO.md](./SLO.md)
- [MONITORING.md](./MONITORING.md)
- [Google Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
- [Google SRE Book - Incident Management](https://sre.google/sre-book/managing-incidents/)
