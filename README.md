# Microservices SRE Project

A production-grade containerized microservices system with Terraform-based infrastructure provisioning, Prometheus/Grafana monitoring, and incident response simulation.

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │              Nginx (Port 80)              │
                    │         Frontend + Reverse Proxy          │
                    └──────┬───────┬──────┬──────┬─────────────┘
                           │       │      │      │
              ┌────────────┘   ┌───┘  ┌───┘  ┌───┘
              ▼               ▼      ▼      ▼
    ┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌───────────┐ ┌──────────┐
    │ Auth Service │ │Product Svc  │ │ Order Svc  │ │ User Svc  │ │ Chat Svc │
    │  Port 8001   │ │ Port 8002   │ │ Port 8003  │ │ Port 8004 │ │ Port 8005│
    └──────┬───────┘ └──────┬──────┘ └─────┬──────┘ └─────┬─────┘ └────┬─────┘
           │                │              │              │             │
           └────────────────┴──────────────┴──────────────┴─────────────┘
                                          │
                                 ┌────────▼────────┐
                                 │   PostgreSQL     │
                                 │   Port 5432      │
                                 └─────────────────┘

    ┌──────────────┐   ┌──────────────────┐
    │  Prometheus  │──▶│     Grafana      │
    │  Port 9090   │   │    Port 3000     │
    └──────────────┘   └──────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx (Frontend) | 80 | UI + Reverse Proxy |
| Auth Service | 8001 | JWT-based authentication |
| Product Service | 8002 | Product catalog CRUD |
| Order Service | 8003 | Order management |
| User Service | 8004 | User profiles |
| Chat Service | 8005 | User messaging + WebSocket |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Dashboards & alerting |
| PostgreSQL | 5432 | Primary database |

## Quick Start

### Prerequisites
- Docker Engine 24+
- Docker Compose v2+

### Run Locally

```bash
# Clone the project
git clone <repo-url>
cd microservices-project

# Start all services
docker compose up -d --build

# Check all containers are running
docker compose ps

# View logs
docker compose logs -f
```

### Access the Application

| URL | Description |
|-----|-------------|
| http://localhost | Frontend UI |
| http://localhost:3000 | Grafana (admin/admin) |
| http://localhost:9090 | Prometheus |
| http://localhost/auth/docs | Auth API Swagger |
| http://localhost/products-svc/docs | Product API Swagger |
| http://localhost/orders-svc/docs | Order API Swagger |

### First Steps

1. Open http://localhost
2. Go to **Auth** → Register a user → Login
3. Go to **Products** → Browse and order
4. Go to **Orders** → View your orders
5. Open **Grafana** at http://localhost:3000 (admin/admin) → Dashboards → Microservices Overview

---

## Incident Response Simulation (Assignment 4)

### Trigger the Incident

```bash
# Stop the order service
docker compose stop order-service

# Restart it with a WRONG database hostname
docker compose run -d \
  -e DATABASE_URL=postgresql://admin:password@wrong-host:5432/microservices \
  -p 8003:8003 \
  --name order-service-broken \
  microservices-project-order-service
```

### Observe in Monitoring

1. Go to Grafana → Microservices Overview dashboard
2. Watch **Order Service Error Rate** spike to 100%
3. Watch **DB Connection Errors** counter increase
4. Prometheus alert `OrderServiceDBConnectionErrors` fires after 30s

### Analyze Logs

```bash
docker logs order-service 2>&1 | tail -30
# You'll see:
# ERROR: could not connect to server: Name or service not known
# Is the server running on host "wrong-host"?
```

### Resolve the Incident

```bash
# Stop broken container
docker compose stop order-service

# Restart with correct configuration
docker compose up -d order-service

# Verify recovery
curl http://localhost/orders-svc/health
# Expected: {"status":"ok","service":"order","db":"connected"}
```

### Using the UI Incident Panel
The frontend has a built-in **Incident Response** tab (⚠️ Incident in the nav) that walks through all 5 phases: Simulate → Detect → Analyze → Mitigate → Postmortem.

---

## Infrastructure as Code (Assignment 5)

### Terraform Setup

```bash
cd terraform

# Copy and fill in your AWS credentials
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Initialize
terraform init

# Preview changes
terraform plan

# Apply (provision infrastructure)
terraform apply

# View outputs (IPs, URLs)
terraform output
```

### Terraform Resources Created

- **EC2 instance** (t3.medium, Ubuntu 22.04) — auto-installs Docker and starts the app
- **Security Group** — opens ports 80, 3000, 9090, 22
- **Elastic IP** — static public IP address
- **Key Pair** — for SSH access

### Tear Down

```bash
terraform destroy
```

---

## Monitoring

### Grafana Dashboard

Open http://localhost:3000 → Login (admin/admin) → Dashboards → Microservices Overview

Panels:
- Service Request Rate (all services)
- Order Service Error Rate (with alert)
- Request Latency P50/P95/P99
- Active Orders gauge
- DB Connection Errors counter
- WebSocket Connections

### Prometheus Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| OrderServiceDBConnectionErrors | > 5 errors/min | Critical |
| OrderServiceHighErrorRate | Any 500 errors | Critical |
| OrderServiceDown | Service unreachable | Critical |
| HighRequestLatency | P99 > 5s | Warning |

---

## API Reference

### Auth Service
```
POST /auth/register  — Register user
POST /auth/login     — Login (returns JWT)
GET  /auth/verify    — Verify JWT token
```

### Product Service
```
GET    /products-svc/products       — List all products
GET    /products-svc/products/{id}  — Get product
POST   /products-svc/products       — Create product
PUT    /products-svc/products/{id}  — Update product
DELETE /products-svc/products/{id}  — Delete product
```

### Order Service
```
GET  /orders-svc/orders             — List orders
GET  /orders-svc/orders/{id}        — Get order
POST /orders-svc/orders             — Create order
PUT  /orders-svc/orders/{id}/status — Update status
```

### Chat Service
```
POST /chat-svc/messages          — Send message
GET  /chat-svc/messages/{uid}    — Get message history
WS   /chat-svc/ws/{uid}         — WebSocket connection
```

---

## Postmortem Summary (INC-2024-001)

**Incident:** Order Service database connection failure due to misconfigured DATABASE_URL  
**Duration:** ~12 minutes  
**Severity:** SEV-2 (High)  
**Impact:** 100% of order creation requests failed  

**Root Cause:** DATABASE_URL environment variable hostname changed to an invalid value during a configuration update.

**Action Items:**
1. Add DB connection validation at service startup
2. Implement Kubernetes readiness probes / Docker healthchecks
3. Reduce Prometheus alert evaluation interval to 30s
4. Add config validation step to CI/CD pipeline
5. Create incident runbook

---

## Project Structure

```
microservices-project/
├── docker-compose.yml
├── README.md
├── services/
│   ├── auth/        (main.py, Dockerfile, requirements.txt)
│   ├── product/     (main.py, Dockerfile, requirements.txt)
│   ├── order/       (main.py, Dockerfile, requirements.txt)
│   ├── user/        (main.py, Dockerfile, requirements.txt)
│   └── chat/        (main.py, Dockerfile, requirements.txt)
├── frontend/
│   └── index.html
├── nginx/
│   └── nginx.conf
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
└── monitoring/
    ├── prometheus/
    │   ├── prometheus.yml
    │   └── alerts.yml
    └── grafana/
        └── provisioning/
            ├── datasources/prometheus.yml
            └── dashboards/
                ├── dashboard.yml
                └── microservices.json
```
