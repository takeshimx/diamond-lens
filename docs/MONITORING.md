# Monitoring Strategy

This document outlines the comprehensive monitoring strategy for the Diamond Lens MLB Stats Assistant application.

## Overview

The monitoring strategy is designed to provide visibility across infrastructure and application layers, enabling proactive issue detection and rapid incident response.

## Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              INFRASTRUCTURE LAYER                            │
│  - Uptime Checks (3 regions)                                │
│  - Cloud Run Metrics (CPU, Memory, Instance Count)          │
│  - Alert Policies (Down, High CPU, High Memory)             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION LAYER                               │
│  - Custom Metrics (Latency, Errors, Processing Time)        │
│  - Structured Logs (JSON, Searchable Fields)                │
│  - Error Classification (bigquery_error, llm_error, etc.)   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA LAYER (Separate ETL Project)               │
│  - Data Freshness Checks                                    │
│  - BigQuery Job Monitoring                                  │
│  - dbt Test Results                                         │
└─────────────────────────────────────────────────────────────┘
```

## Infrastructure Layer Monitoring

### 1. Uptime Checks

**Purpose**: Detect service outages and availability issues

**Configuration**:
- **Backend health check**: `GET /health`
- **Frontend health check**: `GET /`
- **Frequency**: 60 seconds
- **Regions**: USA, EUROPE, ASIA_PACIFIC
- **Timeout**: 10 seconds
- **SSL validation**: Enabled

**Metrics tracked**:
- `monitoring.googleapis.com/uptime_check/check_passed`
- Success rate per region
- Response time per region

**Alert conditions**:
- Service down: < 1 successful check for 60 seconds
- Degraded: Success rate < 90% over 5 minutes

**Implementation**:
- Location: [terraform/modules/monitoring/uptime_checks.tf](../terraform/modules/monitoring/uptime_checks.tf)
- Resources: `google_monitoring_uptime_check_config.backend_health`, `google_monitoring_uptime_check_config.frontend_health`

---

### 2. Cloud Run Metrics

**Purpose**: Monitor container resource utilization and scaling behavior

**Metrics tracked**:

| Metric | Description | Alert Threshold | Action |
|--------|-------------|-----------------|--------|
| `run.googleapis.com/container/memory/utilizations` | Memory usage % | > 80% for 5 min | Increase memory allocation |
| `run.googleapis.com/container/cpu/utilizations` | CPU usage % | > 80% for 5 min | Increase max instances |
| `run.googleapis.com/container/instance_count` | Active instances | > 15 | Review traffic patterns |
| `run.googleapis.com/request_count` | Total requests | - | Baseline tracking |
| `run.googleapis.com/request_latencies` | Request duration | p95 > 5000ms | Performance investigation |

**Dashboard view**:
- Cloud Console → Monitoring → Dashboards → Cloud Run
- Filter: `service_name = mlb-diamond-lens-api OR mlb-diamond-lens-frontend`

**Implementation**:
- Location: [terraform/modules/monitoring/alert_policies.tf](../terraform/modules/monitoring/alert_policies.tf)
- Resources: `google_monitoring_alert_policy.high_memory_usage`, `google_monitoring_alert_policy.high_cpu_usage`

---

## Application Layer Monitoring

### 3. Custom Metrics

**Purpose**: Track application-specific performance and reliability

**Metrics tracked**:

#### 3.1 API Latency (`custom.googleapis.com/diamond-lens/api/latency`)

**Labels**:
- `endpoint`: API endpoint path (e.g., `/api/v1/qa/player-stats`)
- `status_code`: HTTP response code

**Unit**: Milliseconds (ms)

**Aggregation**:
- p50, p95, p99 percentiles
- Mean, min, max

**Alert thresholds**:
- p95 > 6000ms for 5 minutes (SEV-2)
- p99 > 10000ms for 5 minutes (SEV-2)

**Code location**: [backend/app/main.py:51-55](../backend/app/main.py#L51-L55)

---

#### 3.2 API Errors (`custom.googleapis.com/diamond-lens/api/errors`)

**Labels**:
- `endpoint`: API endpoint path
- `error_type`: Classification of error
  - `validation_error`: User input errors
  - `bigquery_error`: Database failures
  - `llm_error`: AI model failures
  - `null_response`: Logic errors

**Unit**: Count (incremental)

**Alert thresholds**:
- Total error rate > 1% for 10 minutes (SEV-2)
- `bigquery_error` count > 5 in 5 minutes (SEV-2)
- `llm_error` count > 10 in 5 minutes (SEV-3)

**Code location**: [backend/app/api/endpoints/ai_analytics_endpoints.py:107](../backend/app/api/endpoints/ai_analytics_endpoints.py#L107)

---

#### 3.3 Query Processing Time (`custom.googleapis.com/diamond-lens/query/processing_time`)

**Labels**:
- `query_type`: Type of query (e.g., `season_batting`, `batting_splits`)

**Unit**: Milliseconds (ms)

**Purpose**: Track end-to-end query processing performance by type

**Analysis**:
- Compare processing time across query types
- Identify slow query types
- Correlate with BigQuery latency

**Code location**: [backend/app/api/endpoints/ai_analytics_endpoints.py:76](../backend/app/api/endpoints/ai_analytics_endpoints.py#L76)

---

#### 3.4 BigQuery Latency (`custom.googleapis.com/diamond-lens/bigquery/latency`)

**Labels**:
- `query_type`: Type of query

**Unit**: Milliseconds (ms)

**Purpose**: Isolate database performance from overall processing time

**Alert threshold**: p95 > 3000ms (investigate query optimization)

**Code location**: [backend/app/api/endpoints/ai_analytics_endpoints.py:77](../backend/app/api/endpoints/ai_analytics_endpoints.py#L77)

---

### 4. Structured Logging

**Purpose**: Enable detailed debugging and log-based analysis

**Format**: JSON (Cloud Logging compatible)

**Standard fields**:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "severity": "INFO",
  "message": "Query processed successfully",
  "query_type": "season_batting",
  "processing_time_ms": 2500.5,
  "bigquery_latency_ms": 1200.3,
  "status_code": 200
}
```

**Severity levels**:
- `DEBUG`: Detailed diagnostics (disabled in production)
- `INFO`: Normal operations (request start/completion)
- `WARNING`: Non-critical issues (retry attempts, fallbacks)
- `ERROR`: Errors requiring attention
- `CRITICAL`: System failures requiring immediate action

**Searchable fields**:
- `jsonPayload.query_type`
- `jsonPayload.error_type`
- `jsonPayload.latency_ms`
- `jsonPayload.status_code`

**Common log queries**:

```bash
# Find all errors in last hour
gcloud logging read "severity=ERROR AND resource.type=cloud_run_revision" \
  --freshness=1h \
  --limit=50

# Find slow queries (> 5 seconds)
gcloud logging read "jsonPayload.processing_time_ms>5000" \
  --limit=50

# Count errors by type
gcloud logging read "jsonPayload.error_type=*" \
  --format=json | jq '.[] | .jsonPayload.error_type' | sort | uniq -c

# View specific query type performance
gcloud logging read "jsonPayload.query_type=batting_splits" \
  --limit=50 \
  --format="table(timestamp, jsonPayload.processing_time_ms)"
```

**Code location**: [backend/app/utils/structured_logger.py](../backend/app/utils/structured_logger.py)

---

## Monitoring Dashboards

### Dashboard 1: Service Health Overview

**Purpose**: High-level service health at a glance

**Widgets**:
1. **Availability Scorecard**: Current uptime %
2. **Error Rate Gauge**: Current error rate vs. SLO
3. **Active Incidents**: Count of open incidents
4. **Request Volume**: Requests per minute (time series)
5. **Latency Distribution**: p50, p95, p99 (time series)

**Refresh**: 1 minute

---

### Dashboard 2: Application Performance

**Purpose**: Detailed application performance metrics

**Widgets**:
1. **Latency by Endpoint**: Heatmap of latency distribution
2. **Query Processing Time**: By query type (stacked time series)
3. **BigQuery Latency**: p95 over time
4. **Error Breakdown**: Pie chart of error types
5. **Slow Queries**: Table of queries > 5s with details

**Refresh**: 1 minute

---

### Dashboard 3: Infrastructure Metrics

**Purpose**: Cloud Run resource utilization

**Widgets**:
1. **Memory Utilization**: Backend vs. Frontend (time series)
2. **CPU Utilization**: Backend vs. Frontend (time series)
3. **Instance Count**: Active instances over time
4. **Request Concurrency**: Concurrent requests per instance
5. **Cold Start Count**: Cold starts per hour

**Refresh**: 1 minute

---

## Alert Notification Channels

### Email Notifications

**Configuration**:
- Type: `email`
- Variable: `notification_email` in Terraform
- Usage: All alert policies

**Email format**:
```
Subject: [ALERT] MLB Diamond Lens - Backend API Down

Policy: Backend API Down Alert
Resource: mlb-diamond-lens-api (Cloud Run service)
Condition: Uptime check failed for 60 seconds
Severity: CRITICAL

View incident: [Cloud Console link]
View logs: [Cloud Logging link]
Runbook: https://github.com/.../docs/INCIDENT_RESPONSE.md
```

**Configuration location**: [terraform/modules/monitoring/alert_policies.tf](../terraform/modules/monitoring/alert_policies.tf)

---

### Future: Slack Integration

**Planned features**:
- Real-time alert notifications to #alerts channel
- Incident thread creation for collaboration
- Alert acknowledgment via Slack commands
- Status updates posted automatically

**Implementation**: Add `google_monitoring_notification_channel` with type `slack`

---

## Log Retention and Export

### Cloud Logging Retention

**Default retention**: 30 days

**Recommendation**: Export logs to BigQuery for long-term analysis

### BigQuery Export Setup

```bash
# Create log sink to BigQuery
gcloud logging sinks create diamond-lens-logs-sink \
  bigquery.googleapis.com/projects/tksm-dash-test-25/datasets/application_logs \
  --log-filter='resource.type="cloud_run_revision" AND (resource.labels.service_name="mlb-diamond-lens-api" OR resource.labels.service_name="mlb-diamond-lens-frontend")'
```

**Analysis queries**:
```sql
-- Average latency by day
SELECT
  DATE(timestamp) as date,
  AVG(CAST(jsonPayload.latency_ms AS FLOAT64)) as avg_latency_ms
FROM `tksm-dash-test-25.application_logs.cloud_run_revision_*`
WHERE jsonPayload.latency_ms IS NOT NULL
GROUP BY date
ORDER BY date DESC;

-- Error rate by hour
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
  COUNTIF(severity = 'ERROR') as error_count,
  COUNT(*) as total_count,
  SAFE_DIVIDE(COUNTIF(severity = 'ERROR'), COUNT(*)) * 100 as error_rate_pct
FROM `tksm-dash-test-25.application_logs.cloud_run_revision_*`
GROUP BY hour
ORDER BY hour DESC;
```

---

## Monitoring Best Practices

### 1. Alert Fatigue Prevention

**Problem**: Too many alerts reduce response effectiveness

**Solutions**:
- Set alert thresholds based on SLO impact (not arbitrary values)
- Use appropriate time windows (avoid alerting on transient spikes)
- Group related alerts (don't create separate alerts for correlated issues)
- Implement alert suppression during known maintenance windows

**Current configuration**:
- All alerts have minimum 60-second duration thresholds
- High memory/CPU alerts require 5-minute sustained violation
- Auto-close after 30 minutes of normal operation

---

### 2. Actionable Alerts

**Every alert should have**:
- Clear description of what's wrong
- Link to runbook with investigation steps
- Severity level guiding response urgency
- Expected resolution time

**Example** (from alert policy):
```hcl
documentation {
  content = <<-EOT
    Backend API is not responding to health checks.

    Severity: CRITICAL (SEV-1)

    Investigation steps:
    1. Check Cloud Run service status
    2. Review application logs for errors
    3. Verify dependencies (BigQuery, Gemini API)

    Runbook: https://github.com/.../docs/INCIDENT_RESPONSE.md#alert-backend-api-down
  EOT
}
```

---

### 3. Metric Collection Efficiency

**Avoid**:
- High-cardinality labels (e.g., user_id, query_text)
- Excessive metric writes (> 1/second per metric)
- Unbounded label values

**Current design**:
- Limited labels: `endpoint`, `status_code`, `query_type`, `error_type`
- Metric writes only on request completion (not per-second)
- Bounded label values (query types are predefined in `query_maps.py`)

---

### 4. Cost Optimization

**Cloud Monitoring costs**:
- Chargeable metrics: Custom metrics (> 150 per billing account)
- Log ingestion: $0.50 per GiB (after free tier)

**Current usage estimate**:
- Custom metrics: 4 types × 10 label combinations = 40 time series (within free tier)
- Log volume: ~500 MB/month (within free tier for low traffic)

**Cost controls**:
- Structured logging only for essential fields
- Log sampling for DEBUG logs (if enabled)
- Metric aggregation before write (not per-request writes)

---

## Monitoring Gaps and Future Improvements

### Current Gaps

1. **User Experience Monitoring**
   - No frontend performance tracking (page load time, interaction latency)
   - Solution: Add Real User Monitoring (RUM) with Google Analytics or custom metrics

2. **Synthetic Monitoring**
   - Uptime checks only verify health endpoints, not full user flows
   - Solution: Implement synthetic transactions (full query execution tests)

3. **Dependency Monitoring**
   - No direct monitoring of Gemini API or BigQuery health
   - Solution: Add health check wrappers with timeout tracking

4. **Business Metrics**
   - No tracking of query success rate, popular players, query patterns
   - Solution: Add business-level custom metrics

### Planned Improvements

**TBD**:
- [ ] Implement SLO-based alerting in Cloud Monitoring
- [ ] Create custom dashboard for SLO compliance
- [ ] Add synthetic monitoring for critical user flows

**TBD**:
- [ ] Frontend performance monitoring (Core Web Vitals)
- [ ] BigQuery query performance tracking
- [ ] Business metrics dashboard

---

## Testing Monitoring

### Verify Metrics Collection

```bash
# Check custom metrics are being written
gcloud monitoring time-series list \
  --filter='metric.type=starts_with("custom.googleapis.com/diamond-lens")' \
  --interval-start-time="$(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --interval-end-time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Trigger Test Alerts

```bash
# Test backend down alert (stop service temporarily)
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --min-instances=0 \
  --max-instances=0

# Wait 2 minutes for alert to trigger

# Restore service
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --min-instances=0 \
  --max-instances=20
```

### Verify Log Collection

```bash
# Generate test log
curl -X POST https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/api/v1/qa/player-stats \
  -H "Content-Type: application/json" \
  -d '{"query": "大谷翔平の2024年の打率は？", "season": 2024}'

# Check log appears (wait 30 seconds)
gcloud logging read "jsonPayload.query=*" --limit=1 --freshness=1m
```

---

## References

- [SLO.md](./SLO.md) - Service Level Objectives
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) - Incident response runbooks
- [Google Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [Cloud Logging Best Practices](https://cloud.google.com/logging/docs/best-practices)
- [Terraform Monitoring Module](../terraform/modules/monitoring/)

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-01-15 | 1.0 | Initial monitoring strategy | - |
