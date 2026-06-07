"""
main.py
-------
FastAPI backend for LastBite.
Sets up the web server, SQLite database, and all API endpoints.

Endpoints:
    POST   /api/scan          — scan a fridge photo with GPT-4o Vision
    GET    /api/pantry        — list all pantry items
    POST   /api/pantry        — add one item manually
    POST   /api/pantry/bulk   — add multiple items (after scan)
    DELETE /api/pantry        — clear all pantry items
    DELETE /api/pantry/{id}   — remove a single item
    GET    /api/runway        — get survival runway stats
    GET    /api/recipes       — get AI-generated recipe suggestions
"""

import base64
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()  # Load OPENAI_API_KEY from .env file

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai_service import get_recipe_suggestions, scan_image_for_food
from freshness import calculate_survival_runway, get_freshness_days

DB_PATH = "lastbite.db"


# ── Database ───────────────────────────────────────────────────────────────────

def init_db():
    """Create the pantry table if it doesn't exist. Runs on server start."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pantry_items (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT    NOT NULL,
            quantity       TEXT    NOT NULL DEFAULT '1',
            detected_date  TEXT    NOT NULL,
            freshness_days INTEGER NOT NULL,
            category       TEXT    NOT NULL DEFAULT 'other'
        )
    """)
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LastBite", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/index.html")


# ── Models ─────────────────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    name: str
    quantity: str = "1"
    category: str = "other"


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_conn():
    """Open a database connection with dict-style row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def enrich(row: sqlite3.Row) -> dict:
    """Add days_remaining and status fields to a pantry row."""
    d = dict(row)
    detected = datetime.strptime(d["detected_date"], "%Y-%m-%d").date()
    remaining = d["freshness_days"] - (date.today() - detected).days
    d["days_remaining"] = remaining
    d["status"] = "fresh" if remaining > 3 else "expiring" if remaining > 0 else "expired"
    return d


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/api/scan")
async def scan(file: UploadFile = File(...)):
    """Send uploaded image to GPT-4o Vision and return detected food items with quantities."""
    data = await file.read()
    b64  = base64.b64encode(data).decode()
    mime = file.content_type or "image/jpeg"
    items = await scan_image_for_food(b64, mime)
    return {"detected": items}


@app.get("/api/pantry")
async def list_pantry():
    """Return all pantry items with freshness status."""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM pantry_items ORDER BY detected_date").fetchall()
        return {"items": [enrich(r) for r in rows]}
    finally:
        conn.close()


@app.post("/api/pantry")
async def add_item(item: ItemCreate):
    """Add a single food item. Freshness days are looked up automatically."""
    conn  = get_conn()
    today = date.today().isoformat()
    fd    = get_freshness_days(item.name)
    try:
        cur = conn.execute(
            "INSERT INTO pantry_items (name, quantity, detected_date, freshness_days, category) VALUES (?,?,?,?,?)",
            (item.name, item.quantity, today, fd, item.category),
        )
        conn.commit()
        return {"id": cur.lastrowid, "freshness_days": fd}
    finally:
        conn.close()


@app.post("/api/pantry/bulk")
async def add_items_bulk(items: list[ItemCreate]):
    """Add multiple items at once after a scan is confirmed."""
    conn  = get_conn()
    today = date.today().isoformat()
    added = []
    try:
        for item in items:
            fd  = get_freshness_days(item.name)
            cur = conn.execute(
                "INSERT INTO pantry_items (name, quantity, detected_date, freshness_days, category) VALUES (?,?,?,?,?)",
                (item.name, item.quantity, today, fd, item.category),
            )
            added.append({"id": cur.lastrowid, "name": item.name})
        conn.commit()
        return {"added": added}
    finally:
        conn.close()


@app.delete("/api/pantry")
async def clear_pantry():
    """Delete all items from the pantry."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM pantry_items")
        conn.commit()
        return {"cleared": True}
    finally:
        conn.close()


@app.delete("/api/pantry/{item_id}")
async def delete_item(item_id: int):
    """Delete a single pantry item by ID."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM pantry_items WHERE id = ?", (item_id,))
        conn.commit()
        return {"deleted": item_id}
    finally:
        conn.close()


@app.get("/api/runway")
async def runway():
    """Calculate survival runway from current pantry contents."""
    conn = get_conn()
    try:
        rows  = conn.execute("SELECT * FROM pantry_items").fetchall()
        items = [enrich(r) for r in rows]
    finally:
        conn.close()
    return calculate_survival_runway(items)


@app.get("/api/recipes")
async def recipes():
    """Return AI-generated recipe suggestions based on pantry contents."""
    conn = get_conn()
    try:
        rows  = conn.execute("SELECT * FROM pantry_items").fetchall()
        items = [enrich(r) for r in rows]
    finally:
        conn.close()

    available = [i for i in items if i["days_remaining"] > 0]
    if not available:
        return {"recipes": [], "message": "Pantry is empty"}

    return {"recipes": await get_recipe_suggestions(available)}
