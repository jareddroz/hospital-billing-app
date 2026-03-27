import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

import os

# Create database folder if not exists
if not os.path.exists("database"):
    os.makedirs("database")

conn = sqlite3.connect("database/hospital.db", check_same_thread=False)
cursor = conn.cursor()

# MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="Hospital Billing App", layout="wide")

if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# -------------------------------
# Login State
# -------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

# -------------------------------
# DATABASE SETUP
# -------------------------------
conn = sqlite3.connect("database/hospital.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    time TEXT,
    patient_name TEXT,
    amount REAL,
    payment_mode TEXT,
    doctor_name TEXT,
    receipt_number TEXT,
    purpose TEXT,
    entered_by TEXT
)
""")

conn.commit()

# -------------------------------
# USERS TABLE (for login)
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

conn.commit()

# -------------------------------
# INSERT DEFAULT USERS
# -------------------------------
cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("reception", "1234"))
cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("manager", "1234"))

conn.commit()


# -------------------------------
# Login Screen
# ------------------------------- 

if not st.session_state.logged_in:
    st.title("🔐 Hospital Login")

    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username_input, password_input)
        )
        user = cursor.fetchone()

        if user:
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.success("Login successful ✅")
            st.rerun()
        else:
            st.error("Invalid credentials ❌")

    st.stop()

# -------------------------------
# Logout
# ------------------------------- 

st.sidebar.write(f"Logged in as: {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

# -------------------------------
# UI SECTION
# -------------------------------
#st.set_page_config(page_title="Hospital Billing App", layout="wide")

st.title("🏥 Hospital Billing System")
st.write("Enter transaction details below:")

# Input fields
patient_name = st.text_input("Patient Name")
amount = st.number_input("Amount", min_value=0.0)
payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI"])
doctor_name = st.text_input("Doctor Name")
receipt_number = st.text_input("Receipt Number")
purpose = st.text_input("Purpose")

# -------------------------------
# SUBMIT BUTTON (SAVE DATA)
# -------------------------------
entered_by = st.session_state.username

if st.button("Submit"):

    current_datetime = datetime.now()
    date = current_datetime.strftime("%Y-%m-%d")
    time = current_datetime.strftime("%H:%M:%S")

    cursor.execute("""
    INSERT INTO transactions 
    (date, time, patient_name, amount, payment_mode, doctor_name, receipt_number, purpose, entered_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (date, time, patient_name, amount, payment_mode, doctor_name, receipt_number, purpose, entered_by))

    conn.commit()

    st.success("Transaction Saved Successfully ✅")

# -------------------------------
# Edit Data and Delete Data
# -------------------------------

st.header("📊 All Transactions")

df = pd.read_sql_query("SELECT * FROM transactions", conn)

if not df.empty:
    for index, row in df.iterrows():

        if st.session_state.edit_id == row['id']:
            # EDIT MODE
            st.write(f"✏️ Editing Transaction ID: {row['id']}")

            new_patient = st.text_input("Patient Name", row['patient_name'], key=f"patient_{row['id']}")
            new_amount = st.number_input("Amount", value=row['amount'], key=f"amount_{row['id']}")
            new_mode = st.selectbox("Payment Mode", ["Cash", "UPI"], index=0 if row['payment_mode']=="Cash" else 1, key=f"mode_{row['id']}")
            new_doctor = st.text_input("Doctor Name", row['doctor_name'], key=f"doctor_{row['id']}")
            new_receipt = st.text_input("Receipt Number", row['receipt_number'], key=f"receipt_{row['id']}")
            new_purpose = st.text_input("Purpose", row['purpose'], key=f"purpose_{row['id']}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Save", key=f"save_{row['id']}"):
                    cursor.execute("""
                    UPDATE transactions
                    SET patient_name=?, amount=?, payment_mode=?, doctor_name=?, receipt_number=?, purpose=?
                    WHERE id=?
                    """, (new_patient, new_amount, new_mode, new_doctor, new_receipt, new_purpose, row['id']))
                    
                    conn.commit()
                    st.success("Updated successfully ✅")
                    st.session_state.edit_id = None
                    st.rerun()

            with col2:
                if st.button("Cancel", key=f"cancel_{row['id']}"):
                    st.session_state.edit_id = None
                    st.rerun()

        else:
            # NORMAL VIEW
            st.write(f"**Patient:** {row['patient_name']} | **Amount:** {row['amount']} | **Mode:** {row['payment_mode']} | **Doctor:** {row['doctor_name']}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Edit", key=f"edit_{row['id']}"):
                    st.session_state.edit_id = row['id']

            with col2:
                if st.button("Delete", key=f"delete_{row['id']}"):
                    cursor.execute("DELETE FROM transactions WHERE id = ?", (row['id'],))
                    conn.commit()
                    st.warning("Transaction Deleted")
                    st.rerun()

        st.markdown("---")
else:
    st.info("No transactions available")


# -------------------------------
# Reports - Dashboard
# -------------------------------

st.header("📊 Reports Dashboard")

### Daily Total
# Convert date column to datetime
df['date'] = pd.to_datetime(df['date'])

# Get today's date
today = pd.to_datetime("today").date()

# Filter today's data
today_df = df[df['date'].dt.date == today]

# Calculate total
daily_total = today_df['amount'].sum()

st.metric("💰 Today's Total Collection", f"{daily_total:.2f}")

### Cash vs UPI
cash_total = df[df['payment_mode'] == "Cash"]['amount'].sum()
upi_total = df[df['payment_mode'] == "UPI"]['amount'].sum()

col1, col2 = st.columns(2)

with col1:
    st.metric("💵 Cash Collection", f"{cash_total:.2f}")

with col2:
    st.metric("📱 UPI Collection", f"{upi_total:.2f}")

### User-wise Collection
user_summary = df.groupby('entered_by')['amount'].sum().reset_index()

st.subheader("👤 Collection by User")
st.dataframe(user_summary)


