# Assignment 4 — Incident Response Report & Postmortem

---

## Part 1: Incident Report

### 1. Incident Summary

**Incident ID:** INC-2024-001  
**Date:** 2024-04-15  
**Reporter:** On-Call SRE Engineer  
**Status:** Resolved  

On April 15, 2024, the Order Service experienced a complete outage due to a database misconfiguration. The environment variable `DATABASE_URL` was set to an invalid hostname (`wrong-host` instead of `postgres`), causing all database connections to fail immediately. This resulted in 100% of order creation and retrieval requests returning HTTP 500 errors.

---

### 2. Impact Assessment

| Category | Detail |
|----------|--------|
| **Affected Service** | Order Service (order-service, port 8003) |
| **User-Facing Impact** | Users could not create, view, or manage orders |
| **Other Services** | Auth, Product, User, Chat — unaffected |
| **Data Loss** | None — PostgreSQL was healthy; only the connection was broken |
| **Revenue Impact** | 100% order functionality unavailable during incident window |
| **Duration** | ~12 minutes (T+0:00 to T+12:00) |

---

### 3. Severity Classification

**Severity: SEV-2 (High)**

Justification:
- Core business functionality (ordering) completely unavailable
- 100% error rate on all Order Service endpoints
- No automatic mitigation or fallback
- Affected all users system-wide
- Not SEV-1 because: other services remained healthy; database data was intact; no data corruption occurred

---

### 4. Timeline of Events

| Time (T+) | Event |
|-----------|-------|
| T+0:00 | Configuration change deployed — ORDER_SERVICE `DATABASE_URL` set to `wrong-host` |
| T+0:05 | Order Service container restarts with new config |
| T+0:10 | First HTTP 500 errors appear on POST /orders |
| T+0:30 | Prometheus alert `OrderServiceDBConnectionErrors` fires |
| T+0:35 | Prometheus alert `OrderServiceHighErrorRate` fires |
| T+1:00 | Grafana dashboard shows red on Order Service error panel |
| T+2:00 | On-call engineer paged via alert notification |
| T+3:00 | Engineer acknowledges incident, begins investigation |
| T+5:00 | Container logs examined: `could not connect to server: Name or service not known (wrong-host)` |
| T+7:00 | Root cause identified: incorrect DATABASE_URL |
| T+8:00 | Configuration corrected in docker-compose.yml |
| T+9:00 | Order Service restarted: `docker compose up -d order-service` |
| T+10:00 | Order Service health check returns `{"status":"ok","db":"connected"}` |
| T+11:00 | Test orders placed successfully via UI and API |
| T+12:00 | Incident declared resolved; monitoring confirmed stable |

---

### 5. Root Cause Analysis

**Primary Cause:**  
The `DATABASE_URL` environment variable in `docker-compose.yml` was changed from the correct value:
```
postgresql://admin:password@postgres:5432/microservices
```
to an invalid hostname:
```
postgresql://admin:password@wrong-host:5432/microservices
```

When the Order Service started, every attempt to connect to PostgreSQL failed with a DNS resolution error since `wrong-host` does not exist in the Docker network.

**Why It Wasn't Caught Earlier:**
- No startup health check validated DB connectivity before the service began accepting traffic
- No CI/CD pipeline step validated the configuration before deployment
- Nginx did not fail-safe: it still routed traffic to the Order Service even though it was returning 500s
- Detection relied on Prometheus polling (15s interval), adding latency to alert firing

**Why It Affected All Requests:**
PostgreSQL uses a connection-per-request pattern in this implementation (no connection pool), so every incoming request attempted a fresh DB connection and failed immediately.

---

### 6. Mitigation Steps

```bash
# Step 1: Identify the broken container
docker compose ps
# order-service shows as running but unhealthy

# Step 2: Read container logs
docker logs order-service --tail 50
# Output:
# ERROR: could not connect to server: Name or service not known
# Is the server running on host "wrong-host" and accepting
# TCP/IP connections on port 5432?

# Step 3: Inspect environment variables
docker inspect order-service | grep -A1 DATABASE_URL
# Found: "DATABASE_URL=postgresql://admin:password@wrong-host:5432/microservices"

# Step 4: Fix docker-compose.yml
# Changed: @wrong-host:5432 → @postgres:5432

# Step 5: Restart service
docker compose stop order-service
docker compose up -d order-service

# Step 6: Verify
curl http://localhost/orders-svc/health
# {"status":"ok","service":"order","db":"connected"}
```

---

### 7. Resolution Confirmation

✅ Order Service health endpoint returns `{"status":"ok","db":"connected"}`  
✅ POST /orders returns 200 with new order ID  
✅ GET /orders returns order list  
✅ Prometheus `order_db_connection_errors_total` stops increasing  
✅ Grafana error rate panel returns to 0  
✅ All other services confirmed unaffected  

---

## Part 2: Postmortem Analysis

### 1. Incident Overview

This postmortem covers INC-2024-001, a 12-minute outage of the Order Service caused by a misconfigured database connection string. The service was fully restored with a configuration fix and container restart.

---

### 2. Customer Impact

- **Orders affected:** All order operations (create, list, view) returned HTTP 500 during the incident window
- **Authentication:** Unaffected — users could still log in
- **Product browsing:** Unaffected — users could still view products
- **Chat:** Unaffected
- **Estimated failed requests:** ~100% of order requests during 12-minute window
- **User experience:** Users saw generic error messages when attempting to place orders

---

### 3. Root Cause Analysis

The core failure was a configuration error introduced during a manual environment variable update. The Docker Compose file was edited directly without a validation step, and the change was deployed immediately.

The system lacked:
1. **Startup validation** — the service should refuse to start if DB is unreachable
2. **Config linting** — no tool checked that `DATABASE_URL` pointed to a reachable host
3. **Readiness probes** — Docker has no healthcheck on the order-service container
4. **Gradual rollout** — the new config was applied all-at-once with no canary

---

### 4. Detection and Response Evaluation

**What worked well:**
- Prometheus collected metrics at 5s intervals for the Order Service (faster than default)
- Alerts were pre-configured and fired within 30 seconds of the first error
- Grafana dashboard made the error rate spike immediately visible
- Container logs clearly showed the exact misconfiguration

**What could be improved:**
- Alert-to-page latency was ~2 minutes — too slow for a critical service
- No automated remediation attempted (could have auto-restarted with last known-good config)
- On-call engineer was not immediately aware of which config changed

---

### 5. Resolution Summary

The incident was resolved by:
1. Reading container logs to identify the wrong hostname
2. Correcting `DATABASE_URL` in `docker-compose.yml`
3. Restarting the Order Service container
4. Verifying recovery via health endpoint and test orders

Total MTTR: **12 minutes**  
Time to detect: **~2 minutes**  
Time to diagnose: **~5 minutes**  
Time to fix and verify: **~5 minutes**

---

### 6. Lessons Learned

1. **Configuration changes are deployment events.** Any change to environment variables must go through a review and validation process — not direct file edits.

2. **Services should fail fast and loudly.** If the database is not reachable at startup, the service should refuse to start (exit code non-zero), triggering a container restart loop that is easily visible.

3. **Detection time must be faster.** A 2-minute detection window for a P0 service is too slow. Alerts should fire within 30 seconds and pages within 1 minute.

4. **Runbooks save time.** An engineer unfamiliar with the system spent 3+ minutes determining the root cause. A runbook with "check DB connectivity → inspect DATABASE_URL" would have cut this in half.

5. **Monitoring should cover config health.** A custom metric that validates the DB hostname at startup would have immediately surfaced the misconfiguration.

---

### 7. Action Items

| ID | Action | Owner | Priority | Due Date |
|----|--------|-------|----------|----------|
| AI-001 | Add DB connectivity check at startup (fail container if DB unreachable) | Backend Team | P0 — Critical | Week 1 |
| AI-002 | Add Docker healthcheck to order-service in docker-compose.yml | DevOps | P0 — Critical | Week 1 |
| AI-003 | Add config validation script that runs before `docker compose up` | DevOps | P0 — Critical | Week 1 |
| AI-004 | Reduce Prometheus scrape interval to 5s and alert `for` to 15s | SRE | P1 — High | Week 2 |
| AI-005 | Create incident runbook: "Order Service DB Connection Failure" | SRE | P1 — High | Week 2 |
| AI-006 | Implement change management process for docker-compose.yml edits | Engineering Lead | P1 — High | Week 2 |
| AI-007 | Add PagerDuty/Opsgenie integration to Grafana alerts | SRE | P2 — Medium | Month 1 |
| AI-008 | Evaluate connection pooling (PgBouncer) to reduce per-request DB connections | Backend Team | P2 — Medium | Month 1 |

---

### Appendix: Prometheus Queries Used During Investigation

```promql
# Error rate during incident
rate(order_requests_total{status="500"}[1m])

# DB connection errors
increase(order_db_connection_errors_total[5m])

# Was service up?
up{job="order-service"}

# P99 latency (would be near timeout during incident)
histogram_quantile(0.99, rate(order_request_duration_seconds_bucket[5m]))
```
