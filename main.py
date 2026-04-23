from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from fastapi.responses import FileResponse 
from datetime import datetime

app = FastAPI()

# 1. CORS Middleware (Must be before routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Database Initialization
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            hourly_pay REAL DEFAULT 11.44,
            current_balance REAL DEFAULT 0,
            rent REAL DEFAULT 0,
            rent_paid_months TEXT DEFAULT '[]'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            hours REAL,
            description TEXT,
            paid BOOLEAN DEFAULT 0
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (id, hourly_pay, current_balance, rent) VALUES (1, 11.44, 0, 0)")
    conn.commit()
    conn.close()

init_db()

# 3. Data Models
class WorkEntry(BaseModel):
    date: str
    hours: float
    description: Optional[str] = ""

class RateUpdate(BaseModel):
    hourly_pay: float

class RentUpdate(BaseModel):
    rent: float

class BalanceUpdate(BaseModel):
    starting_balance: float

# 4. Routes
@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/api/settings")
def get_settings():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    res = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    data = dict(res)
    import json
    data['rent_paid_months'] = json.loads(data['rent_paid_months'])
    return data

@app.post("/api/work-entry")
def add_work(entry: WorkEntry):
    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO work_entries (date, hours, description) VALUES (?, ?, ?)",
                 (entry.date, entry.hours, entry.description))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/work-entries")
def get_work(month: str):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    res = conn.execute("""
        SELECT *, (hours * (SELECT hourly_pay FROM settings)) as earnings 
        FROM work_entries WHERE date LIKE ?
    """, (f"{month}%",)).fetchall()
    conn.close()
    return [dict(r) for r in res]

@app.get("/api/weekly-summary")
def get_summary(date: str):
    # This matches the frontend's expected structure
    return {"total_hours": 0.0, "hours_remaining": 20.0, "total_earnings": 0.0, "over_limit": False}

@app.get("/api/expenses")
def get_expenses():
    return [] # Placeholder for future expense logic

@app.post("/api/settings/hourly-pay")
def update_pay(data: RateUpdate):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE settings SET hourly_pay = ? WHERE id = 1", (data.hourly_pay,))
    conn.commit()
    conn.close()
    return {"message": "Rate updated"}

@app.post("/api/settings/rent")
def update_rent(data: RentUpdate):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE settings SET rent = ? WHERE id = 1", (data.rent,))
    conn.commit()
    conn.close()
    return {"message": "Rent updated"}

@app.post("/api/settings/starting-balance")
def update_balance(data: BalanceUpdate):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE settings SET current_balance = ? WHERE id = 1", (data.starting_balance,))
    conn.commit()
    conn.close()
    return {"message": "Balance updated"}

@app.post("/api/receive-last-month-pay")
def receive_pay():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    # Logic: find unpaid entries, sum them, add to balance, mark as paid
    unpaid = cursor.execute("SELECT id, hours FROM work_entries WHERE paid = 0").fetchall()
    if not unpaid:
        return {"message": "No unpaid earnings found", "entries_paid": 0}
    
    rate = cursor.execute("SELECT hourly_pay FROM settings").fetchone()[0]
    total_to_add = sum([row[1] for row in unpaid]) * rate
    
    cursor.execute("UPDATE settings SET current_balance = current_balance + ?", (total_to_add,))
    cursor.execute("UPDATE work_entries SET paid = 1 WHERE paid = 0")
    conn.commit()
    conn.close()
    return {"message": f"Received £{total_to_add:.2f}", "entries_paid": len(unpaid)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)