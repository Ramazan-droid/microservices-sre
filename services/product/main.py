from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import os
import psycopg2
import psycopg2.extras
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Product Service")

DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/microservices")

REQUEST_COUNT = Counter("product_requests_total", "Total product requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("product_request_duration_seconds", "Product request latency")

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int = 0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None

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
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    stock INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Insert sample products
            cur.execute("SELECT COUNT(*) FROM products")
            count = cur.fetchone()[0]
            if count == 0:
                sample_products = [
                    ("Laptop Pro X", "High performance laptop", 1299.99, 50),
                    ("Wireless Mouse", "Ergonomic wireless mouse", 39.99, 200),
                    ("Mechanical Keyboard", "RGB mechanical keyboard", 89.99, 150),
                    ("4K Monitor", "27-inch 4K IPS monitor", 449.99, 75),
                    ("USB-C Hub", "7-in-1 USB-C hub", 59.99, 300),
                    ("Webcam HD", "1080p HD webcam", 79.99, 120),
                    ("Headphones Pro", "Noise canceling headphones", 199.99, 90),
                    ("SSD 1TB", "NVMe SSD 1TB", 129.99, 200),
                ]
                for p in sample_products:
                    cur.execute(
                        "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s)",
                        p
                    )
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Product tables created")
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
    return {"status": "ok", "service": "product"}

@app.get("/products")
def list_products():
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id")
        products = cur.fetchall()
        conn.close()
        REQUEST_COUNT.labels("GET", "/products", "200").inc()
        return {"products": [dict(p) for p in products]}
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/products", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.get("/products/{product_id}")
def get_product(product_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        conn.close()
        if not product:
            REQUEST_COUNT.labels("GET", "/products/{id}", "404").inc()
            raise HTTPException(status_code=404, detail="Product not found")
        REQUEST_COUNT.labels("GET", "/products/{id}", "200").inc()
        return dict(product)
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/products/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.post("/products")
def create_product(product: ProductCreate):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s) RETURNING id",
            (product.name, product.description, product.price, product.stock)
        )
        product_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        REQUEST_COUNT.labels("POST", "/products", "201").inc()
        return {"message": "Product created", "product_id": product_id}
    except Exception as e:
        REQUEST_COUNT.labels("POST", "/products", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.put("/products/{product_id}")
def update_product(product_id: int, update: ProductUpdate):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        fields = {k: v for k, v in update.dict().items() if v is not None}
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [product_id]
        cur.execute(f"UPDATE products SET {set_clause} WHERE id = %s", values)
        conn.commit()
        conn.close()
        REQUEST_COUNT.labels("PUT", "/products/{id}", "200").inc()
        return {"message": "Product updated"}
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("PUT", "/products/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        conn.close()
        REQUEST_COUNT.labels("DELETE", "/products/{id}", "200").inc()
        return {"message": "Product deleted"}
    except Exception as e:
        REQUEST_COUNT.labels("DELETE", "/products/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)
