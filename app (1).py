import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

TWILIO_SID = "AC_YOUR_TWILIO_SID_HERE"
TWILIO_AUTH = "YOUR_TWILIO_AUTH_TOKEN_HERE"
TWILIO_PHONE = "+14176076960"

MODEL_FILE = "cyclone_model.joblib"
USERS_FILE = "users.csv"

SIMULATION_MODE = "YOUR_TWILIO" in TWILIO_SID
# ==========================================

st.set_page_config(page_title="Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🔐 SESSION INIT (CRITICAL FIX)
# ==========================================
for key in ["logged_in", "loc_name", "cur_pres"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ==========================================
# 🔐 USER STORAGE
# ==========================================
if not os.path.exists(USERS_FILE):
    pd.DataFrame(
        columns=["Name", "Phone", "Email", "Password", "Created"]
    ).to_csv(USERS_FILE, index=False)

def signup(name, phone, email, password):
    df = pd.read_csv(USERS_FILE)
    if email in df["Email"].values:
        return False
    df.loc[len(df)] = [name, phone, email, password, datetime.now()]
    df.to_csv(USERS_FILE, index=False)
    return True

def login(email, password):
    df = pd.read_csv(USERS_FILE)
    return ((df.Email == email) & (df.Password == password)).any()

# ==========================================
# 🔐 LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 Cyclone Predictor Login")

    t1, t2 = st.tabs(["Login", "Sign Up"])

    with t1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(email, password):
                st.session_state.logged_in = True
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with t2:
        name = st.text_input("Full Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email ID")
        password = st.text_input("Create Password", type="password")

        if st.button("Sign Up"):
            if name and phone and email and password:
                if signup(name, phone, email, password):
                    st.success("Account created. Login now.")
                else:
                    st.error("Email already registered")
            else:
                st.warning("Fill all fields")

    st.stop()  # ⛔ VERY IMPORTANT

# ==========================================
# 🌪️ MAIN APP
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

if not os.path.exists(MODEL_FILE):
    st.error("Model file missing")
    st.stop()

model = joblib.load(MODEL_FILE)

# ==========================================
# 📊 SIDEBAR
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
phone_1 = st.sidebar.text_input("Primary", "+919999999999")
phone_2 = st.sidebar.text_input("Family", "")
phone_3 = st.sidebar.text_input("Authority", "")

# ==========================================
# 🆘 SOS FUNCTION (FIXED)
# ==========================================
def send_sms(phone, location, pressure):
    if SIMULATION_MODE:
        return "SIMULATION"

    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(
            body=f"🚨 CYCLONE SOS\nLocation: {location}\nPressure: {pressure} hPa",
            from_=TWILIO_PHONE,
            to=phone
        )
        return "SENT"
    except Exception as e:
        return str(e)

# ==========================================
# 🆘 SOS BUTTON
# ==========================================
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS", use_container_width=True):
    contacts = [p for p in [phone_1, phone_2, phone_3] if len(p) > 5]
    for p in contacts:
        result = send_sms(p, st.session_state.loc_name, st.session_state.cur_pres)
        if result == "SENT":
            st.sidebar.success(f"SOS sent to {p}")
        elif result == "SIMULATION":
            st.sidebar.info(f"[Simulation] SOS → {p}")
        else:
            st.sidebar.error(result)

# ==========================================
# 🌍 WEATHER DATA
# ==========================================
lat, lon, pres = 17.7, 83.3, 1012
location = "Vizag (Default)"

if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("City", "Visakhapatnam")
    r = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    )
    if r.status_code == 200:
        d = r.json()
        lat, lon, pres = d["coord"]["lat"], d["coord"]["lon"], d["main"]["pressure"]
        location = d["name"]

else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, lat)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, lon)
    pres = st.sidebar.slider("Pressure", 900, 1020, pres)
    location = "Custom Simulation"

st.session_state.loc_name = location
st.session_state.cur_pres = pres

# ==========================================
# 🔮 PREDICTION (SAFE)
# ==========================================
features = [[lat, lon, pres]]
pred = model.predict(features)[0]

try:
    conf = np.max(model.predict_proba(features)[0]) * 100
except:
    conf = 75.0

labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]

# ==========================================
# 📊 DASHBOARD
# ==========================================
c1, c2 = st.columns([1, 2])

with c1:
    st.subheader(location)
    st.metric("Pressure", f"{pres} hPa")
    st.write(f"## {labels[pred]}")
    st.write(f"Confidence: {conf:.1f}%")

with c2:
    m = folium.Map(location=[lat, lon], zoom_start=10)
    folium.Marker([lat, lon], popup=location).add_to(m)
    st_folium(m, width=800, height=500)
