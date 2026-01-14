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

# Replace with your actual credentials
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE = "+15075195618"

MODEL_FILE = "cyclone_model.joblib"
USERS_FILE = "users.csv"

# Check if Twilio is configured
SIMULATION_MODE = "YOUR_TWILIO" in TWILIO_SID

st.set_page_config(page_title="Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🔐 SESSION INIT (FIXED)
# ==========================================
# Added all necessary keys to prevent "KeyError" or "AttributeError"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "loc_name" not in st.session_state:
    st.session_state.loc_name = "Unknown"
if "cur_pres" not in st.session_state:
    st.session_state.cur_pres = 1012

# ==========================================
# 🔐 USER STORAGE
# ==========================================
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["Name", "Phone", "Email", "Password", "Created"]).to_csv(USERS_FILE, index=False)

def signup(name, phone, email, password):
    df = pd.read_csv(USERS_FILE)
    if email in df["Email"].values:
        return False
    # Using concat instead of .loc for better pandas compatibility
    new_user = pd.DataFrame([[name, phone, email, password, datetime.now()]], 
                            columns=["Name", "Phone", "Email", "Password", "Created"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True

def login(email, password):
    df = pd.read_csv(USERS_FILE)
    # Convert to string to ensure comparison works
    user_match = df[(df["Email"] == email) & (df["Password"] == str(password))]
    return not user_match.empty

# ==========================================
# 🔐 LOGIN/SIGNUP UI
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 Cyclone Predictor Login")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    
    with t1:
        l_email = st.text_input("Email", key="login_email")
        l_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if login(l_email, l_pass):
                st.session_state.logged_in = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    with t2:
        s_name = st.text_input("Full Name")
        s_phone = st.text_input("Phone Number")
        s_email = st.text_input("Email ID")
        s_pass = st.text_input("Create Password", type="password")
        if st.button("Sign Up"):
            if s_name and s_phone and s_email and s_pass:
                if signup(s_name, s_phone, s_email, s_pass):
                    st.success("Account created! Please log in.")
                else:
                    st.error("Email already exists.")
            else:
                st.warning("Please fill all fields.")
    st.stop()

# ==========================================
# 🌪️ MAIN APP CONTENT
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

# Model Loading with Error Handling
try:
    if os.path.exists(MODEL_FILE):
        model = joblib.load(MODEL_FILE)
    else:
        st.error(f"Error: {MODEL_FILE} not found. Please upload the model file.")
        st.stop()
except Exception as e:
    st.error(f"Failed to load model: {e}")
    st.stop()

# ==========================================
# 📊 SIDEBAR
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
p1 = st.sidebar.text_input("Primary Contact", "+919999999999")
p2 = st.sidebar.text_input("Family Contact", "")

# SOS Function
def trigger_sos(target_phone, location, pressure, label):
    if SIMULATION_MODE:
        return "SIMULATION"
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        # 1. SMS Alert (English)
        client.messages.create(
            body=f"🚨 SOS: Cyclone Risk Detected!\nStatus: {label}\nLocation: {location}\nPressure: {pressure} hPa",
            from_=TWILIO_PHONE,
            to=target_phone
        )
        # 2. Voice Alert (Hindi) - Per your instructions
        call_content = f'<Response><Say language="hi-IN">Chetavani! {location} mein chakravaat ka khatra hai.</Say></Response>'
        client.calls.create(twiml=call_content, to=target_phone, from_=TWILIO_PHONE)
        return "SUCCESS"
    except Exception as e:
        return str(e)

# ==========================================
# 🌍 DATA ACQUISITION
# ==========================================
lat, lon, pres = 17.7, 83.3, 1012
loc_display = "Visakhapatnam"

if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("Enter City", "Visakhapatnam")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    try:
        res = requests.get(url).json()
        if res.get("cod") == 200:
            lat, lon, pres = res["coord"]["lat"], res["coord"]["lon"], res["main"]["pressure"]
            loc_display = res["name"]
        else:
            st.sidebar.error("City not found. Using default.")
    except:
        st.sidebar.error("Network error.")

else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012)
    loc_display = "Simulation Area"

st.session_state.loc_name = loc_display
st.session_state.cur_pres = pres

# ==========================================
# 🔮 PREDICTION & DASHBOARD
# ==========================================
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
features = np.array([[lat, lon, pres]])
prediction_idx = model.predict(features)[0]
current_status = labels[prediction_idx]

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Atmospheric Pressure", f"{pres} hPa")
    st.markdown(f"### Current Status: {current_status}")
    
    if prediction_idx >= 2:
        st.warning("⚠️ HIGH RISK! SOS triggers are active.")

    if st.button("🚨 TRIGGER SOS NOW", use_container_width=True):
        targets = [p for p in [p1, p2] if len(p) > 5]
        for t in targets:
            status = trigger_sos(t, loc_display, pres, current_status)
            if status == "SUCCESS":
                st.success(f"SOS Sent to {t}")
            elif status == "SIMULATION":
                st.info(f"Simulated SOS to {t}")
            else:
                st.error(f"Failed {t}: {status}")

with col2:
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker([lat, lon], popup=loc_display).add_to(m)
    st_folium(m, width=700, height=450)