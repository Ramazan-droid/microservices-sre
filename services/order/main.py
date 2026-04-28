from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import os
import psycopg2
import psycopg2.extras
import logging
from typing import Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Order Service")

# This DATABASE_URL can be misconfigured to simulate incident
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/microservices")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8002")

REQUEST_COUNT = Counter("order_requests_total", "Total order requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("order_request_duration_seconds", "Order request latency")
ORDER_FAILURES = Counter("order_failures_total", "Total order failures")
DB_CONNECTION_ERRORS = Counter("order_db_connection_errors_total", "DB connection errors")
ACTIVE_ORDERS = Gauge("order_active_orders", "Number of active orders")

class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int

class OrderStatus(BaseModel):
    status: str

def get_db():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()

def create_tables():
    for attempt in range(10):
        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    total_price DECIMAL(10,2),
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Order tables created successfully")
            return
        except Exception as e:
            logger.warning(f"DB not ready (attempt {attempt+1}): {e}")
            time.sleep(3)

@app.on_event("startup")
async def startup():
    create_tables()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    try:
        conn = psycopg2.connect(DB_URL)
        conn.close()
        return {"status": "ok", "service": "order", "db": "connected"}
    except Exception as e:
        DB_CONNECTION_ERRORS.inc()
        logger.error(f"Health check DB failure: {e}")
        return {"status": "degraded", "service": "order", "db": "disconnected", "error": str(e)}

@app.get("/orders")
def list_orders(user_id: Optional[int] = None):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id:
            cur.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
        orders = cur.fetchall()
        conn.close()
        REQUEST_COUNT.labels("GET", "/orders", "200").inc()
        return {"orders": [dict(o) for o in orders]}
    except Exception as e:
        DB_CONNECTION_ERRORS.inc()
        ORDER_FAILURES.inc()
        logger.error(f"Failed to list orders: {e}")
        REQUEST_COUNT.labels("GET", "/orders", "500").inc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        order = cur.fetchone()
        conn.close()
        if not order:
            REQUEST_COUNT.labels("GET", "/orders/{id}", "404").inc()
            raise HTTPException(status_code=404, detail="Order not found")
        REQUEST_COUNT.labels("GET", "/orders/{id}", "200").inc()
        return dict(order)
    except HTTPException:
        raise
    except Exception as e:
        DB_CONNECTION_ERRORS.inc()
        ORDER_FAILURES.inc()
        logger.error(f"Failed to get order {order_id}: {e}")
        REQUEST_COUNT.labels("GET", "/orders/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.post("/orders")
def create_order(order: OrderCreate):
    start = time.time()
    try:
        # Get product info
        try:
            product_resp = requests.get(f"{PRODUCT_SERVICE_URL}/products/{order.product_id}", timeout=5)
            if product_resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Product not found")
            product = product_resp.json()
            total_price = product["price"] * order.quantity
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Could not reach product service: {e}")
            total_price = 0.0

        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO orders (user_id, product_id, quantity, total_price, status)
               VALUES (%s, %s, %s, %s, 'pending') RETURNING id""",
            (order.user_id, order.product_id, order.quantity, total_price)
        )
        order_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        ACTIVE_ORDERS.inc()
        REQUEST_COUNT.labels("POST", "/orders", "201").inc()
        return {"message": "Order created", "order_id": order_id, "total_price": total_price}
    except HTTPException:
        raise
    except Exception as e:
        DB_CONNECTION_ERRORS.inc()
        ORDER_FAILURES.inc()
        logger.error(f"Failed to create order: {e}")
        REQUEST_COUNT.labels("POST", "/orders", "500").inc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.put("/orders/{order_id}/status")
def update_order_status(order_id: int, status_update: OrderStatus):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s",
            (status_update.status, order_id)
        )
        conn.commit()
        conn.close()
        if status_update.status in ("completed", "cancelled"):
            ACTIVE_ORDERS.dec()
        REQUEST_COUNT.labels("PUT", "/orders/{id}/status", "200").inc()
        return {"message": "Order status updated"}
    except Exception as e:
        DB_CONNECTION_ERRORS.inc()
        ORDER_FAILURES.inc()
        logger.error(f"Failed to update order {order_id}: {e}")
        REQUEST_COUNT.labels("PUT", "/orders/{id}/status", "500").inc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        REQUEST_LATENCY.observe(time.time() - start)
