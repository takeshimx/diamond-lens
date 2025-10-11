# Service Level Objectives (SLO)

This document defines the Service Level Objectives for the Diamond Lens MLB Stats Assistant application.

## Overview

SLOs define the target reliability and performance levels for the application. These objectives guide operational decisions, alert thresholds, and incident response priorities.

## SLO Framework

**Error Budget**: 0.1% (99.9% availability) = 43.8 minutes downtime per month

## Service Level Indicators (SLIs) and Objectives (SLOs)

### 1. Availability

**Definition**: Percentage of successful requests (HTTP 200-299) over total requests

**SLI**: `(successful_requests / total_requests) * 100`

**SLO**: 99.9% availability over 30-day rolling window

**Measurement**:
- **Success criteria**: HTTP status codes 200-299
- **Failure criteria**: HTTP status codes 500-599, timeouts
- **Exclusions**: HTTP 400-499 (client errors)

**Monitoring**:
```
# Cloud Monitoring query
sum(rate(api_requests{status_code=~"2.."}[30d])) / sum(rate(api_requests[30d]))
```

**Alert threshold**: < 99.5% (50% error budget consumed)

---

### 2. Latency

**Definition**: 95th percentile API response time

**SLI**: `p95(request_latency_ms)`

**SLO**:
- **p95 latency**: < 5000ms (5 seconds)
- **p99 latency**: < 8000ms (8 seconds)

**Measurement**:
- Start: Request received by API
- End: Response sent to client
- Includes: LLM processing, BigQuery queries, response generation

**Monitoring**:
```
# Custom metric
custom.googleapis.com/diamond-lens/api/latency
```

**Alert threshold**:
- p95 > 6000ms (sustained for 5 minutes)
- p99 > 10000ms (sustained for 5 minutes)

**Rationale**:
- AI-powered query processing requires LLM calls (1-3s) + BigQuery execution (1-3s)
- 5s p95 provides good user experience while accounting for complex queries

---

### 3. Error Rate

**Definition**: Percentage of requests resulting in errors

**SLI**: `(error_requests / total_requests) * 100`

**SLO**: < 0.5% error rate over 1-hour window

**Error classification**:
- `validation_error`: Input validation failures (not counted - user error)
- `bigquery_error`: Database failures (counted)
- `llm_error`: AI model failures (counted)
- `null_response`: Service logic errors (counted)

**Monitoring**:
```
# Custom metric
custom.googleapis.com/diamond-lens/api/errors
```

**Alert threshold**: > 1% error rate sustained for 10 minutes

---

### 4. Data Freshness

**Definition**: Time since last successful data update in BigQuery

**SLI**: `current_time - last_update_timestamp`

**SLO**: < 24 hours data lag

**Measurement**:
- Query: `SELECT MAX(game_date) FROM fact_batting_stats_with_risp`
- Compare with current date

**Monitoring**: Manual check or scheduled query in separate ETL project

**Alert threshold**: > 48 hours (data critically stale)

**Note**: This SLO is monitored in the ETL/dbt project, not this application

---

## SLO Compliance Monitoring

### Monthly SLO Review

**Review schedule**: First Monday of each month

**Review items**:
1. SLO achievement vs. targets
2. Error budget consumption
3. Incident impact on SLOs
4. SLO threshold adjustments (if needed)

### Dashboard Metrics

**Key metrics to display**:
- Current month availability: 99.95%
- Error budget remaining: 80%
- p95 latency trend (last 7 days)
- Error rate by error type
- Incident count and MTTR

**Dashboard location**:
```
Cloud Console → Monitoring → Dashboards → Diamond Lens SLO Dashboard
```

---

## Error Budget Policy

### Error Budget Allocation

**Total monthly budget**: 43.8 minutes of downtime

**Allocation**:
- **Planned maintenance**: 20 minutes (45%)
- **Unplanned incidents**: 20 minutes (45%)
- **Buffer**: 3.8 minutes (10%)

### Budget Consumption Actions

| Budget Remaining | Actions |
|------------------|---------|
| > 50% | Normal operations, continue feature development |
| 25-50% | Increase monitoring frequency, defer risky deployments |
| 10-25% | Freeze feature releases, focus on reliability improvements |
| < 10% | Emergency protocol: no changes except critical fixes |

### Budget Reset

Error budget resets monthly (1st day of each month at 00:00 UTC)

---

## SLO Exceptions

**Excluded from SLO calculations**:

1. **Planned maintenance windows**
   - Announced 48 hours in advance
   - Maximum 20 minutes per month
   - Scheduled during low-traffic periods (JST 3:00-5:00 AM)

2. **Client errors (HTTP 4xx)**
   - User input validation failures
   - Authentication failures
   - Rate limiting

3. **Third-party service outages**
   - Google Cloud Platform outages (Gemini API, BigQuery)
   - DNS failures outside our control

**Documentation required**: All exceptions must be logged in incident reports

---

## SLO Dependencies

### External Dependencies

| Service | SLO Impact | Mitigation |
|---------|------------|------------|
| **Gemini API** | High (LLM processing) | Retry logic, exponential backoff |
| **BigQuery** | High (data retrieval) | Query optimization, connection pooling |
| **Cloud Run** | Critical (hosting) | Multi-region deployment (future) |
| **Cloud Logging** | Low (observability) | Local fallback logging |

### Internal Dependencies

| Component | SLO Impact | Mitigation |
|-----------|------------|------------|
| **query_maps.py** | High (SQL generation) | Schema validation gate in CI/CD |
| **ai_service.py** | Critical (core logic) | Unit tests (49 tests) |
| **BigQuery schema** | High (data access) | Automated schema validation |

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-01-15 | 1.0 | Initial SLO definition | - |

---

## References

- [Google SRE Book - Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md)
