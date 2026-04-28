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

app = FastAPI(title="User Service")
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/microservices")

REQUEST_COUNT = Counter("user_requests_total", "Total user requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("user_request_duration_seconds", "User request latency")

class UserProfile(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None

def create_tables():
    for attempt in range(10):
        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE,
                    username VARCHAR(100),
                    email VARCHAR(200),
                    full_name VARCHAR(200),
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("User profile tables created")
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
    return {"status": "ok", "service": "user"}

@app.get("/users")
def list_users():
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM user_profiles ORDER BY id")
        users = cur.fetchall()
        conn.close()
        REQUEST_COUNT.labels("GET", "/users", "200").inc()
        return {"users": [dict(u) for u in users]}
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/users", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.get("/users/{user_id}")
def get_user(user_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        conn.close()
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found")
        REQUEST_COUNT.labels("GET", "/users/{id}", "200").inc()
        return dict(user)
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/users/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.post("/users")
def create_user_profile(user_id: int, profile: UserProfile):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_profiles (user_id, username, email, full_name, bio)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (user_id, profile.username, profile.email, profile.full_name, profile.bio)
        )
        profile_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        REQUEST_COUNT.labels("POST", "/users", "201").inc()
        return {"message": "Profile created", "profile_id": profile_id}
    except psycopg2.errors.UniqueViolation:
        REQUEST_COUNT.labels("POST", "/users", "400").inc()
        raise HTTPException(status_code=400, detail="Profile already exists")
    except Exception as e:
        REQUEST_COUNT.labels("POST", "/users", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.put("/users/{user_id}")
def update_user_profile(user_id: int, profile: UserProfile):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            """UPDATE user_profiles SET full_name=%s, bio=%s, updated_at=NOW()
               WHERE user_id=%s""",
            (profile.full_name, profile.bio, user_id)
        )
        conn.commit()
        conn.close()
        REQUEST_COUNT.labels("PUT", "/users/{id}", "200").inc()
        return {"message": "Profile updated"}
    except Exception as e:
        REQUEST_COUNT.labels("PUT", "/users/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)
