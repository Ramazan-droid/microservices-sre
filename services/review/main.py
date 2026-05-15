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

app = FastAPI(title="Review Service")

DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/microservices")

REQUEST_COUNT = Counter("review_requests_total", "Total review requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("review_request_duration_seconds", "Review request latency")


class ReviewCreate(BaseModel):
    product_id: int
    user_id: int
    rating: int       # 1–5
    comment: Optional[str] = ""


def create_tables():
    for attempt in range(10):
        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            # Insert sample reviews
            cur.execute("SELECT COUNT(*) FROM reviews")
            count = cur.fetchone()[0]
            if count == 0:
                sample_reviews = [
                    (1, 1, 5, "Amazing laptop, super fast!"),
                    (1, 2, 4, "Great build quality, a bit pricey"),
                    (2, 1, 5, "Best mouse I have ever used"),
                    (3, 3, 3, "Good keyboard but loud switches"),
                    (4, 2, 5, "Stunning display, worth every penny"),
                    (5, 1, 4, "Very useful hub, works perfectly"),
                ]
                for r in sample_reviews:
                    cur.execute(
                        "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (%s, %s, %s, %s)",
                        r
                    )
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Review tables created")
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
    return {"status": "ok", "service": "review"}


@app.get("/reviews")
def list_reviews(product_id: Optional[int] = None):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if product_id:
            cur.execute("SELECT * FROM reviews WHERE product_id = %s ORDER BY created_at DESC", (product_id,))
        else:
            cur.execute("SELECT * FROM reviews ORDER BY created_at DESC")
        reviews = cur.fetchall()
        conn.close()
        REQUEST_COUNT.labels("GET", "/reviews", "200").inc()
        return {"reviews": [dict(r) for r in reviews]}
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/reviews", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)


@app.get("/reviews/{review_id}")
def get_review(review_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM reviews WHERE id = %s", (review_id,))
        review = cur.fetchone()
        conn.close()
        if not review:
            REQUEST_COUNT.labels("GET", "/reviews/{id}", "404").inc()
            raise HTTPException(status_code=404, detail="Review not found")
        REQUEST_COUNT.labels("GET", "/reviews/{id}", "200").inc()
        return dict(review)
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/reviews/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)


@app.post("/reviews")
def create_review(review: ReviewCreate):
    start = time.time()
    try:
        if not 1 <= review.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (%s, %s, %s, %s) RETURNING id",
            (review.product_id, review.user_id, review.rating, review.comment)
        )
        review_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        REQUEST_COUNT.labels("POST", "/reviews", "201").inc()
        return {"message": "Review created", "review_id": review_id}
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("POST", "/reviews", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)


@app.delete("/reviews/{review_id}")
def delete_review(review_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM reviews WHERE id = %s RETURNING id", (review_id,))
        deleted = cur.fetchone()
        conn.commit()
        conn.close()
        if not deleted:
            REQUEST_COUNT.labels("DELETE", "/reviews/{id}", "404").inc()
            raise HTTPException(status_code=404, detail="Review not found")
        REQUEST_COUNT.labels("DELETE", "/reviews/{id}", "200").inc()
        return {"message": "Review deleted"}
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("DELETE", "/reviews/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)