from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            hourly_pay REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            rent REAL DEFAULT 0,
            rent_paid_months TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            hours REAL,
            description TEXT,
            earnings REAL,
            paid INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT
        )
    """)

    cursor.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")
    conn.commit()
    conn.close()

init_db()

# ---------------- MODELS ----------------

class WorkEntry(BaseModel):
    date: str
    hours: float
    description: str = ""

class ExpenseRequest(BaseModel):
    category: str
    amount: float
    description: str = ""

class HourlyPayRequest(BaseModel):
    hourly_pay: float

class RentRequest(BaseModel):
    rent: float

class BalanceRequest(BaseModel):
    starting_balance: float

class RentApplyRequest(BaseModel):
    month: str

class PayRequest(BaseModel):
    pay_up_to_date: str

# ---------------- ROUTES ----------------

@app.get("/")
def index():
    return FileResponse("index.html")

@app.get("/api/settings")
def get_settings():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()

    rent_paid = row["rent_paid_months"].split(",") if row["rent_paid_months"] else []

    return {
        "hourly_pay": row["hourly_pay"],
        "current_balance": row["current_balance"],
        "rent": row["rent"],
        "rent_paid_months": rent_paid
    }

@app.post("/api/settings/hourly-pay")
def set_hourly(req: HourlyPayRequest):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE settings SET hourly_pay = ? WHERE id = 1", (req.hourly_pay,))
    conn.commit()
    conn.close()
    return {"message": "Hourly pay updated"}

@app.post("/api/settings/rent")
def set_rent(req: RentRequest):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE settings SET rent = ? WHERE id = 1", (req.rent,))
    conn.commit()
    conn.close()
    return {"message": "Rent updated"}

@app.post("/api/settings/starting-balance")
def set_balance(req: BalanceRequest):
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE settings SET current_balance = ? WHERE id = 1", (req.starting_balance,))
    conn.commit()
    conn.close()
    return {"message": "Balance updated"}

@app.post("/api/work-entry")
def add_work(entry: WorkEntry):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    hourly = conn.execute("SELECT hourly_pay FROM settings WHERE id = 1").fetchone()[0]
    earnings = entry.hours * hourly

    conn.execute("""
        INSERT INTO work_entries (date, hours, description, earnings)
        VALUES (?, ?, ?, ?)
    """, (entry.date, entry.hours, entry.description, earnings))

    conn.commit()
    conn.close()

    return {"message": "Work entry added"}

@app.get("/api/work-entries")
def get_entries(month: str):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT * FROM work_entries
        WHERE date LIKE ?
        ORDER BY date DESC
    """, (f"{month}%",)).fetchall()

    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/weekly-summary")
def weekly_summary(date: str):
    d = datetime.strptime(date, "%Y-%m-%d")
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT * FROM work_entries
        WHERE date BETWEEN ? AND ?
    """, (monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d"))).fetchall()

    conn.close()

    total_hours = sum(r["hours"] for r in rows)
    total_earnings = sum(r["earnings"] for r in rows)
    hours_remaining = 20 - total_hours

    return {
        "total_hours": total_hours,
        "total_earnings": total_earnings,
        "hours_remaining": hours_remaining,
        "over_limit": total_hours > 20
    }

@app.post("/api/receive-last-month-pay")
def receive_pay(req: PayRequest):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT * FROM work_entries
        WHERE date <= ? AND paid = 0
    """, (req.pay_up_to_date,)).fetchall()

    total = sum(r["earnings"] for r in rows)

    conn.execute("UPDATE settings SET current_balance = current_balance + ? WHERE id = 1", (total,))
    conn.execute("UPDATE work_entries SET paid = 1 WHERE date <= ?", (req.pay_up_to_date,))

    conn.commit()
    conn.close()

    return {"message": f"Paid £{total:.2f}", "entries_paid": len(rows)}

@app.post("/api/apply-rent")
def apply_rent(req: RentApplyRequest):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT rent, rent_paid_months FROM settings WHERE id = 1").fetchone()
    rent = row["rent"]
    paid_months = row["rent_paid_months"].split(",") if row["rent_paid_months"] else []

    if req.month in paid_months:
        return {"message": "Rent already applied"}

    conn.execute("UPDATE settings SET current_balance = current_balance - ? WHERE id = 1", (rent,))
    paid_months.append(req.month)
    conn.execute("UPDATE settings SET rent_paid_months = ? WHERE id = 1", (",".join(paid_months),))

    conn.commit()
    conn.close()

    return {"message": f"Rent £{rent:.2f} applied"}

@app.post("/api/apply-expense")
def apply_expense(req: ExpenseRequest):
    conn = sqlite3.connect("database.db")

    today = datetime.now().strftime("%Y-%m-%d")

    conn.execute("""
        INSERT INTO expenses (date, category, amount, description)
        VALUES (?, ?, ?, ?)
    """, (today, req.category, req.amount, req.description))

    conn.execute("UPDATE settings SET current_balance = current_balance - ? WHERE id = 1", (req.amount,))

    conn.commit()
    conn.close()

    return {"message": "Expense added"}

@app.get("/api/expenses")
def get_expenses(month: str):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT * FROM expenses
        WHERE date LIKE ?
        ORDER BY date DESC
    """, (f"{month}%",)).fetchall()

    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)