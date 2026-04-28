from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import os
import psycopg2
import psycopg2.extras
import logging
from typing import List, Dict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chat Service")
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/microservices")

REQUEST_COUNT = Counter("chat_requests_total", "Total chat requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("chat_request_duration_seconds", "Chat request latency")
ACTIVE_CONNECTIONS = Gauge("chat_active_websocket_connections", "Active WebSocket connections")
MESSAGES_TOTAL = Counter("chat_messages_total", "Total messages sent")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        ACTIVE_CONNECTIONS.inc()
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
        ACTIVE_CONNECTIONS.dec()
        logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(message)

    async def broadcast(self, message: str):
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                await connection.send_text(message)

manager = ConnectionManager()

class MessageCreate(BaseModel):
    sender_id: int
    receiver_id: int
    content: str

def create_tables():
    for attempt in range(10):
        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Chat tables created")
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
    return {"status": "ok", "service": "chat", "active_connections": sum(len(v) for v in manager.active_connections.values())}

@app.post("/messages")
def send_message(msg: MessageCreate):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages (sender_id, receiver_id, content) VALUES (%s, %s, %s) RETURNING id",
            (msg.sender_id, msg.receiver_id, msg.content)
        )
        msg_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        MESSAGES_TOTAL.inc()
        REQUEST_COUNT.labels("POST", "/messages", "201").inc()
        return {"message_id": msg_id, "status": "sent"}
    except Exception as e:
        REQUEST_COUNT.labels("POST", "/messages", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.get("/messages/{user_id}")
def get_messages(user_id: int, other_user_id: int):
    start = time.time()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM messages
            WHERE (sender_id = %s AND receiver_id = %s)
               OR (sender_id = %s AND receiver_id = %s)
            ORDER BY created_at ASC
        """, (user_id, other_user_id, other_user_id, user_id))
        messages = cur.fetchall()
        conn.close()
        REQUEST_COUNT.labels("GET", "/messages/{id}", "200").inc()
        return {"messages": [dict(m) for m in messages]}
    except Exception as e:
        REQUEST_COUNT.labels("GET", "/messages/{id}", "500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.observe(time.time() - start)

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            # Store message
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (sender_id, receiver_id, content) VALUES (%s, %s, %s) RETURNING id",
                (user_id, msg_data.get("receiver_id", 0), msg_data.get("content", ""))
            )
            conn.commit()
            conn.close()
            MESSAGES_TOTAL.inc()
            # Send to receiver
            receiver_id = msg_data.get("receiver_id")
            message = json.dumps({
                "from": user_id,
                "content": msg_data.get("content"),
                "timestamp": time.time()
            })
            await manager.send_personal_message(message, receiver_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
