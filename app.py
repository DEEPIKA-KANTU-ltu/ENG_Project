import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Student Budget AI", layout="wide")

st.title("🎓 Student Budget & AI Spending Assistant")

st.write("Manage your income, expenses, and get AI-powered insights to stay on track.")

# -----------------------------
# SESSION STATE INITIALIZATION
# -----------------------------
if "expenses" not in st.session_state:
    st.session_state.expenses = []

# -----------------------------
# INCOME SECTION
# -----------------------------
st.header("💼 Income Calculator")

col1, col2 = st.columns(2)

with col1:
    hours = st.number_input("Hours worked per week", min_value=0.0, step=1.0)
with col2:
    rate = st.number_input("Hourly pay (£)", min_value=0.0, step=1.0)

monthly_income = hours * rate * 4
st.success(f"Estimated Monthly Income: **£{monthly_income:.2f}**")

# -----------------------------
# EXPENSE SECTION
# -----------------------------
st.header("💸 Expense Tracker")

expense_name = st.text_input("Expense name")
expense_amount = st.number_input("Amount (£)", min_value=0.0, step=1.0)

if st.button("Add Expense"):
    if expense_name and expense_amount > 0:
        st.session_state.expenses.append({"name": expense_name, "amount": expense_amount})
        st.success("Expense added!")
    else:
        st.error("Please enter a valid name and amount.")

# Convert to DataFrame
df = pd.DataFrame(st.session_state.expenses)

if not df.empty:
    st.subheader("📊 Your Expenses")
    st.table(df)

    total_expenses = df["amount"].sum()
    st.warning(f"Total Monthly Expenses: **£{total_expenses:.2f}**")

    # Pie chart
    fig = px.pie(df, names="name", values="amount", title="Expense Breakdown")
    st.plotly_chart(fig, use_container_width=True)
else:
    total_expenses = 0

# -----------------------------
# BALANCE + SHORTFALL
# -----------------------------
st.header("📉 Balance Summary")

balance = monthly_income - total_expenses

if balance >= 0:
    st.success(f"Remaining Balance: **£{balance:.2f}**")
else:
    st.error(f"⚠️ You are short by **£{abs(balance):.2f}** this month!")

# -----------------------------
# AI INSIGHTS (Placeholder)
# -----------------------------
st.header("🤖 AI Spending Insights")

st.info("AI insights will appear here once you add your API key.")

# Example AI logic (placeholder)
if not df.empty:
    if total_expenses > monthly_income:
        st.write("🔍 **AI Insight:** Your expenses exceed your income. Consider reducing non-essential spending.")
    elif total_expenses > monthly_income * 0.8:
        st.write("🔍 **AI Insight:** You are close to exceeding your income. Try lowering food or travel costs.")
    else:
        st.write("🔍 **AI Insight:** Your spending is under control. Keep it up!")

st.caption("Prototype v1 — AI integration ready.")
