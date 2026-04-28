from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import jwt
import bcrypt
import time
import os
import psycopg2
import psycopg2.extras
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Auth Service")
security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/microservices")

REQUEST_COUNT = Counter("auth_requests_total", "Total auth requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("auth_request_duration_seconds", "Auth request latency")

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

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
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(200) UNIQUE NOT NULL,
                    password_hash VARCHAR(200) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Auth tables created")
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
    return {"status": "ok", "service": "auth"}

@app.post("/register")
def register(req: RegisterRequest, db=Depends(get_db)):
    start = time.time()
    try:
        hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (req.username, req.email, hashed)
        )
        user_id = cur.fetchone()[0]
        db.commit()
        REQUEST_COUNT.labels("POST", "/register", "200").inc()
        return {"message": "User registered successfully", "user_id": user_id}
    except psycopg2.errors.UniqueViolation:
        db.rollback()
        REQUEST_COUNT.labels("POST", "/register", "400").inc()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    except Exception as e:
        db.rollback()
        REQUEST_COUNT.labels("POST", "/register", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.post("/login")
def login(req: LoginRequest, db=Depends(get_db)):
    start = time.time()
    try:
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (req.username,))
        user = cur.fetchone()
        if not user or not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
            REQUEST_COUNT.labels("POST", "/login", "401").inc()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = jwt.encode(
            {"user_id": user["id"], "username": user["username"], "exp": time.time() + 86400},
            SECRET_KEY, algorithm="HS256"
        )
        REQUEST_COUNT.labels("POST", "/login", "200").inc()
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels("POST", "/login", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.get("/verify")
def verify(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "user_id": payload["user_id"], "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
