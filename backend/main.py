from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
import psycopg2
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = os.getenv("DB_HOST", "postgres_db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

REDIS_HOST = os.getenv("REDIS_HOST", "redis_cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_TLS = os.getenv("REDIS_TLS", "false").lower() == "true"

cache = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    ssl=REDIS_TLS,
    decode_responses=True,
)


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=os.getenv("DB_NAME", "projedb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


@app.on_event("startup")
def startup_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ziyaretciler (
            id SERIAL PRIMARY KEY,
            isim VARCHAR(100)
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ziyaretci/{isim}")
def ziyaretci_ekle(isim: str):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO ziyaretciler (isim) VALUES (%s)",
        (isim,),
    )

    conn.commit()
    cur.close()
    conn.close()

    cache.delete("ziyaretci_listesi")

    return {"mesaj": f"{isim} arşive eklendi!"}


@app.get("/ziyaretciler")
def ziyaretcileri_getir():
    cached_data = cache.get("ziyaretci_listesi")

    if cached_data:
        return {
            "kaynak": "Redis (Çalışma Masası'ndan geldi 🚀)",
            "veriler": json.loads(cached_data),
        }

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT isim FROM ziyaretciler")
    rows = cur.fetchall()

    ziyaretciler = [row[0] for row in rows]

    cur.close()
    conn.close()

    cache.set(
        "ziyaretci_listesi",
        json.dumps(ziyaretciler),
        ex=20,
    )

    return {
        "kaynak": "PostgreSQL (Arşiv Odası'ndan geldi 🐢)",
        "veriler": ziyaretciler,
    }
