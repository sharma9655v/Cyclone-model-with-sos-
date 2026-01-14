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
# 🔑 CONFIGURATION (Use Streamlit Secrets in Production)
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# REPLACE THESE WITH YOUR ACTUAL TWILIO CREDENTIALS
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE = "+15075195618"

MODEL_FILE = "cyclone_model.joblib"
USERS_FILE = "users.csv"

# ==========================================
st.set_page_config(page_title="Cyclone Predictor", page_icon="🌪️", layout="wide")

# 🔐 SESSION INIT
for key in ["logged_in", "loc_name", "cur_pres", "prediction"]:
    if key not in st.session_state:
        st.session_state[key] = None

# 🔐 USER STORAGE
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["Name", "Phone", "Email", "Password", "Created"]).to_csv(USERS_FILE, index=False)

def signup(name, phone, email, password):
    df = pd.read_csv(USERS_FILE)
    if email in df["Email"].values: return False
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
            else: st.error("Invalid credentials")
    with t2:
        name = st.text_input("Full Name")
        phone = st.text_input("Phone")
        u_email = st.text_input("Email ID")
        u_password = st.text_input("Create Password", type="password")
        if st.button("Sign Up"):
            if name and phone and u_email and u_password:
                if signup(name, phone, u_email, u_password): st.success("Account created. Login now.")
                else: st.error("Email already registered")
    st.stop()

# ==========================================
# 🌪️ MAIN APP
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

if not os.path.exists(MODEL_FILE):
    st.error("Model file missing")
    st.stop()

model = joblib.load(MODEL_FILE)

# 📊 SIDEBAR
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
phone_1 = st.sidebar.text_input("Primary Contact (e.g. +91...)", "+919999999999")
phone_2 = st.sidebar.text_input("Family Contact", "")

# ==========================================
# 🆘 SOS FUNCTIONS (TEXT & VOICE)
# ==========================================
def trigger_full_sos(phone, location, pressure, level):
    """Sends English Text and makes a Hindi Voice Call"""
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        
        # 1. Send SMS (English)
        client.messages.create(
            body=f"🚨 CYCLONE SOS ALERT!\nLevel: {level}\nLocation: {location}\nPressure: {pressure} hPa\nImmediate action required!",
            from_=TWILIO_PHONE,
            to=phone
        )
        
        # 2. Optional: Make Voice Call (Hindi)
        # client.calls.create(
        #     twiml=f'<Response><Say language="hi-IN">Saavdhan! {location} me chakravaat ka khatra hai. Kripya surakshit sthaan par jaye.</Say></Response>',
        #     to=phone,
        #     from_=TWILIO_PHONE
        # )
        
        return True
    except Exception as e:
        st.sidebar.error(f"Twilio Error: {e}")
        return False

# SOS BUTTON IN SIDEBAR
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS MANUALLY", use_container_width=True):
    contacts = [p for p in [phone_1, phone_2] if len(p) > 10]
    if not contacts:
        st.sidebar.warning("Please provide valid phone numbers including +country code.")
    else:
        for p in contacts:
            with st.sidebar.spinner(f"Sending to {p}..."):
                if trigger_full_sos(p, st.session_state.loc_name, st.session_state.cur_pres, "MANUAL"):
                    st.sidebar.success(f"✅ SOS Sent to {p}")

# ==========================================
# 🌍 WEATHER DATA & PREDICTION
# ==========================================
lat, lon, pres = 17.7, 83.3, 1012
location = "Vizag (Default)"

if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("City", "Visakhapatnam")
    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}")
    if r.status_code == 200:
        d = r.json()
        lat, lon, pres = d["coord"]["lat"], d["coord"]["lon"], d["main"]["pressure"]
        location = d["name"]
else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012)
    location = "Custom Simulation"

st.session_state.loc_name = location
st.session_state.cur_pres = pres

# PREDICTION
features = [[lat, lon, pres]]
pred = model.predict(features)[0]
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
current_status = labels[pred]

# 📊 DASHBOARD DISPLAY
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader(location)
    st.metric("Pressure", f"{pres} hPa")
    st.write(f"## {current_status}")
    
    # AUTOMATIC TRIGGER FOR CRITICAL STATUS
    if pred >= 2: # STORM or CYCLONE
        st.warning("⚠️ High Risk Detected! Please prepare to trigger SOS.")

with c2:
    m = folium.Map(location=[lat, lon], zoom_start=10)
    folium.Marker([lat, lon], popup=location).add_to(m)
    st_folium(m, width=700, height=450)