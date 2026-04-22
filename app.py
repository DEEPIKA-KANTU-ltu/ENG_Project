import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date, timedelta

# ---------- PAGE CONFIG & CUSTOM STYLE ----------
st.set_page_config(page_title="Student Work & Money Manager", page_icon="💸", layout="wide")

PRIMARY = "#5B21FF"      # bold purple
ACCENT = "#06B6D4"       # teal
DANGER = "#EF4444"       # red
CARD_BG = "#0F172A"      # deep slate
PAGE_BG = "#020617"      # almost black
TEXT_MAIN = "#E5E7EB"    # light gray
TEXT_MUTED = "#9CA3AF"   # muted gray

st.markdown(
    f"""
    <style>
    body {{
        background-color: {PAGE_BG};
    }}
    .main {{
        background-color: {PAGE_BG};
        color: {TEXT_MAIN};
    }}
    .big-title {{
        font-size: 2rem;
        font-weight: 700;
        color: {TEXT_MAIN};
    }}
    .subtitle {{
        font-size: 0.95rem;
        color: {TEXT_MUTED};
    }}
    .card {{
        background: {CARD_BG};
        padding: 1.1rem 1.2rem;
        border-radius: 0.9rem;
        border: 1px solid #1F2937;
    }}
    .calendar-cell {{
        text-align: center;
        padding: 0.25rem 0.1rem;
    }}
    .today-pill {{
        background: {ACCENT};
        color: #0B1120;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.8rem;
    }}
    .day-pill {{
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-size: 0.8rem;
    }}
    .warning-text {{
        color: {DANGER};
        font-weight: 600;
    }}
    .metric-label {{
        font-size: 0.8rem;
        color: {TEXT_MUTED};
    }}
    .metric-value {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {TEXT_MAIN};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- SESSION STATE SETUP ----------
if "hourly_pay" not in st.session_state:
    st.session_state.hourly_pay = 11.44  # default UK min wage-ish
if "starting_balance" not in st.session_state:
    st.session_state.starting_balance = 0.0
if "current_balance" not in st.session_state:
    st.session_state.current_balance = 0.0
if "rent" not in st.session_state:
    st.session_state.rent = 0.0
if "work_log" not in st.session_state:
    st.session_state.work_log = pd.DataFrame(
        columns=["date", "hours", "earnings", "description", "paid"]
    )
if "expenses" not in st.session_state:
    st.session_state.expenses = pd.DataFrame(
        columns=["date", "category", "amount", "description"]
    )
if "current_month" not in st.session_state:
    today = date.today()
    st.session_state.current_month = date(today.year, today.month, 1)
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None


# ---------- HELPER FUNCTIONS ----------
def get_week_range(d: date):
    """Return Monday–Sunday for the week containing date d."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def compute_pending_pay():
    
    df = st.session_state.work_log

    # FIX: if DataFrame is empty or missing 'paid' column
    if df.empty or "paid" not in df.columns:
        return 0.0

    # FIX: ensure no NaN values in 'paid'
    df["paid"] = df["paid"].fillna(False)

    return float(df.loc[~df["paid"], "earnings"].sum())


def compute_week_stats(ref_date: date):
    df = st.session_state.work_log
    if df.empty:
        return 0.0, 0.0
    monday, sunday = get_week_range(ref_date)
    mask = (df["date"] >= pd.to_datetime(monday)) & (df["date"] <= pd.to_datetime(sunday))
    week_df = df.loc[mask]
    return float(week_df["hours"].sum()), float(week_df["earnings"].sum())


def receive_last_month_pay():
    df = st.session_state.work_log
    if df.empty:
        return 0.0

    today = date.today()
    first_this_month = date(today.year, today.month, 1)
    last_month_last_day = first_this_month - timedelta(days=1)
    last_month = last_month_last_day.month
    last_month_year = last_month_last_day.year

    mask = (
        (df["date"].dt.month == last_month)
        & (df["date"].dt.year == last_month_year)
        & (~df["paid"])
    )
    to_pay = df.loc[mask, "earnings"].sum()

    st.session_state.work_log.loc[mask, "paid"] = True
    st.session_state.current_balance += float(to_pay)
    return float(to_pay)


def apply_this_month_rent():
    today = date.today()
    df = st.session_state.expenses
    if st.session_state.rent <= 0:
        return False

    # avoid double-charging rent for same month
    if not df.empty:
        mask = (
            (df["category"] == "Rent")
            & (df["date"].dt.year == today.year)
            & (df["date"].dt.month == today.month)
        )
        if mask.any():
            return False

    new_row = {
        "date": pd.to_datetime(today),
        "category": "Rent",
        "amount": float(st.session_state.rent),
        "description": "Monthly rent",
    }
    st.session_state.expenses = pd.concat(
        [df, pd.DataFrame([new_row])], ignore_index=True
    )
    st.session_state.current_balance -= float(st.session_state.rent)
    return True


def add_work_entry(d: date, hours: float, desc: str):
    earnings = hours * st.session_state.hourly_pay
    new_row = {
        "date": pd.to_datetime(d),
        "hours": float(hours),
        "earnings": float(earnings),
        "description": desc,
        "paid": False,
    }
    st.session_state.work_log = pd.concat(
        [st.session_state.work_log, pd.DataFrame([new_row])], ignore_index=True
    )


def add_expense(category: str, amount: float, desc: str):
    today = date.today()
    new_row = {
        "date": pd.to_datetime(today),
        "category": category,
        "amount": float(amount),
        "description": desc,
    }
    st.session_state.expenses = pd.concat(
        [st.session_state.expenses, pd.DataFrame([new_row])], ignore_index=True
    )
    st.session_state.current_balance -= float(amount)


# ---------- HEADER ----------
col_title, col_meta = st.columns([3, 2])
with col_title:
    st.markdown('<div class="big-title">💸 Student Work & Money Manager</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Track shifts, protect your 20‑hour limit, and see how your money moves without sharing bank details.</div>',
        unsafe_allow_html=True,
    )
with col_meta:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="metric-label">Current balance</span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-value">£{st.session_state.current_balance:,.2f}</div>',
        unsafe_allow_html=True,
    )
    pending = compute_pending_pay()
    st.markdown('<span class="metric-label">Pending pay (next month)</span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-value" style="color:{ACCENT};">£{pending:,.2f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ---------- TOP ROW: SETTINGS + QUICK SUMMARY ----------
left, right = st.columns([2, 3])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ Settings")

    starting = st.number_input(
        "Starting balance (£)",
        min_value=0.0,
        value=float(st.session_state.starting_balance),
        step=10.0,
    )
    if starting != st.session_state.starting_balance and st.session_state.starting_balance == 0:
        # first time set: sync current balance
        st.session_state.starting_balance = starting
        st.session_state.current_balance = starting
    elif starting != st.session_state.starting_balance:
        # later changes: adjust current balance by difference
        diff = starting - st.session_state.starting_balance
        st.session_state.starting_balance = starting
        st.session_state.current_balance += diff

    hourly = st.number_input(
        "Hourly pay (£/hour)",
        min_value=0.0,
        value=float(st.session_state.hourly_pay),
        step=0.5,
    )
    st.session_state.hourly_pay = hourly

    rent_val = st.number_input(
        "Monthly rent (£)",
        min_value=0.0,
        value=float(st.session_state.rent),
        step=10.0,
    )
    st.session_state.rent = rent_val

    if st.button("🏠 Apply this month's rent"):
        if apply_this_month_rent():
            st.success("This month's rent has been applied and deducted from your balance.")
        else:
            st.info("Rent for this month is already applied or rent is £0.")

    if st.button("📥 Receive last month's pay"):
        paid = receive_last_month_pay()
        if paid > 0:
            st.success(f"Added £{paid:,.2f} from last month's shifts to your balance.")
        else:
            st.info("No unpaid shifts found for last month.")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Weekly work summary")

    today = date.today()
    week_hours, week_earnings = compute_week_stats(today)
    wcol1, wcol2, wcol3 = st.columns(3)
    with wcol1:
        st.markdown('<span class="metric-label">Hours this week</span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">{week_hours:.1f} h</div>',
            unsafe_allow_html=True,
        )
    with wcol2:
        st.markdown('<span class="metric-label">Earnings this week</span>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="metric-value">£{week_earnings:,.2f}</div>',
            unsafe_allow_html=True,
        )
    with wcol3:
        limit_left = max(0.0, 20.0 - week_hours)
        st.markdown('<span class="metric-label">Hours left (20h cap)</span>', unsafe_allow_html=True)
        colour = ACCENT if limit_left > 0 else DANGER
        st.markdown(
            f'<div class="metric-value" style="color:{colour};">{limit_left:.1f} h</div>',
            unsafe_allow_html=True,
        )

    if week_hours > 20:
        st.markdown(
            f'<div class="warning-text">⚠ You have exceeded 20 hours this week. Consider reducing shifts next week.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="subtitle">You are within the 20‑hour limit. Keep an eye on this as you add more shifts.</span>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ---------- CALENDAR + WORK ENTRY ----------
cal_col, form_col = st.columns([3, 2])

with cal_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🗓 Shifts calendar")

    # month navigation
    nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
    with nav_c1:
        if st.button("◀ Previous"):
            cm = st.session_state.current_month
            prev_month_last_day = cm - timedelta(days=1)
            st.session_state.current_month = date(prev_month_last_day.year, prev_month_last_day.month, 1)
    with nav_c2:
        cm = st.session_state.current_month
        st.markdown(
            f"<div style='text-align:center; font-weight:600;'>{cm.strftime('%B %Y')}</div>",
            unsafe_allow_html=True,
        )
    with nav_c3:
        if st.button("Next ▶"):
            cm = st.session_state.current_month
            days_in_month = calendar.monthrange(cm.year, cm.month)[1]
            next_month_first = cm + timedelta(days=days_in_month)
            st.session_state.current_month = date(next_month_first.year, next_month_first.month, 1)

    cm = st.session_state.current_month
    cal = calendar.Calendar(firstweekday=0)  # Monday start

    # header row
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hcols = st.columns(7)
    for i, name in enumerate(day_names):
        hcols[i].markdown(
            f"<div class='calendar-cell' style='font-weight:600; color:{TEXT_MUTED};'>{name}</div>",
            unsafe_allow_html=True,
        )

    # calendar grid
    today = date.today()
    for week in cal.monthdatescalendar(cm.year, cm.month):
        cols = st.columns(7)
        for i, d in enumerate(week):
            label = str(d.day)
            is_this_month = d.month == cm.month
            is_today = d == today
            base_style = "calendar-cell"

            if is_today and is_this_month:
                inner = f"<span class='today-pill'>{label}</span>"
            elif is_this_month:
                inner = f"<span class='day-pill' style='border:1px solid #1F2937;'>{label}</span>"
            else:
                inner = f"<span class='day-pill' style='color:{TEXT_MUTED}; opacity:0.4;'>{label}</span>"

            with cols[i]:
                st.markdown(f"<div class='{base_style}'>{inner}</div>", unsafe_allow_html=True)
                if is_this_month:
                    if st.button("Add", key=f"day-{d.isoformat()}"):
                        st.session_state.selected_date = d
    st.markdown('</div>', unsafe_allow_html=True)

with form_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("✏️ Add work hours")

    if st.session_state.selected_date is None:
        st.markdown(
            '<span class="subtitle">Click a day in the calendar to log a shift.</span>',
            unsafe_allow_html=True,
        )
    else:
        sd = st.session_state.selected_date
        st.markdown(
            f"<div class='subtitle'>Adding shift for <b>{sd.strftime('%A %d %B %Y')}</b></div>",
            unsafe_allow_html=True,
        )
        hours = st.number_input("Hours worked", min_value=0.0, step=0.5, key="hours_input")
        desc = st.text_input("Description (optional)", key="desc_input")

        if st.button("Save shift"):
            if hours <= 0:
                st.warning("Please enter a positive number of hours.")
            else:
                add_work_entry(sd, hours, desc)
                st.success("Shift saved. Earnings added to pending pay (next month).")
                st.session_state.selected_date = None

        if st.button("Cancel"):
            st.session_state.selected_date = None

    st.markdown('</div>', unsafe_allow_html=True)

# ---------- EXPENSES ----------
st.markdown("## 🧾 Expenses")

exp_left, exp_right = st.columns([2, 3])

with exp_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Quick add expense")

    st.markdown('<span class="subtitle">Tap a category, then enter the amount.</span>', unsafe_allow_html=True)

    cat_row1 = st.columns(3)
    cat_row2 = st.columns(3)

    categories = [
        ("Travel", "🚍"),
        ("Grocery", "🛒"),
        ("Food", "🍽"),
        ("Shopping", "🛍"),
        ("Bills", "💡"),
        ("Other", "➕"),
    ]

    clicked_category = None
    for (cat, icon), col in zip(categories[:3], cat_row1):
        if col.button(f"{icon} {cat}"):
            clicked_category = cat
    for (cat, icon), col in zip(categories[3:], cat_row2):
        if col.button(f"{icon} {cat}"):
            clicked_category = cat

    if "expense_category" not in st.session_state:
        st.session_state.expense_category = None

    if clicked_category:
        st.session_state.expense_category = clicked_category

    if st.session_state.expense_category:
        st.markdown(
            f"<div class='subtitle'>Adding expense for <b>{st.session_state.expense_category}</b> (today)</div>",
            unsafe_allow_html=True,
        )
        amt = st.number_input("Amount (£)", min_value=0.0, step=1.0, key="expense_amount")
        edesc = st.text_input("Description (optional)", key="expense_desc")

        if st.button("Save expense"):
            if amt <= 0:
                st.warning("Please enter a positive amount.")
            else:
                add_expense(st.session_state.expense_category, amt, edesc)
                st.success("Expense saved and deducted from your balance.")
                st.session_state.expense_category = None

        if st.button("Cancel expense"):
            st.session_state.expense_category = None

    st.markdown('</div>', unsafe_allow_html=True)

with exp_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Expense history")

    df_exp = st.session_state.expenses.copy()
    if df_exp.empty:
        st.markdown('<span class="subtitle">No expenses recorded yet.</span>', unsafe_allow_html=True)
    else:
        df_exp = df_exp.sort_values("date", ascending=False)
        df_exp["date"] = df_exp["date"].dt.date
        st.dataframe(
            df_exp,
            use_container_width=True,
            hide_index=True,
        )
        total_exp = float(df_exp["amount"].sum())
        st.markdown(
            f"<div class='subtitle'>Total recorded expenses: <b>£{total_exp:,.2f}</b></div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- WORK LOG TABLE ----------
st.markdown("## 🧑‍💻 Work log")

st.markdown('<div class="card">', unsafe_allow_html=True)
df_work = st.session_state.work_log.copy()
if df_work.empty:
    st.markdown('<span class="subtitle">No shifts recorded yet. Start by clicking a date in the calendar.</span>', unsafe_allow_html=True)
else:
    df_work = df_work.sort_values("date", ascending=False)
    df_work["date"] = df_work["date"].dt.date
    df_work["status"] = df_work["paid"].map({True: "Paid", False: "Pending"})
    st.dataframe(
        df_work[["date", "hours", "earnings", "description", "status"]],
        use_container_width=True,
        hide_index=True,
    )
st.markdown('</div>', unsafe_allow_html=True)
