import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
TWILIO_SID = "AC_YOUR_TWILIO_SID_HERE"
TWILIO_AUTH = "YOUR_TWILIO_AUTH_TOKEN_HERE"
TWILIO_PHONE = "+1234567890"

CSV_FILE_NAME = 'ibtracs.NI.list.v04r01.zip' 
MODEL_FILE_NAME = 'cyclone_model.joblib'
# ==========================================

# 1. PAGE CONFIG
st.set_page_config(page_title="Cyclone Predictor", page_icon="🌪️", layout="wide")
st.title("🌪️ North Indian Ocean Cyclone Predictor")

# 2. CHECK FILES
if not os.path.exists(MODEL_FILE_NAME):
    st.error(f"❌ CRITICAL ERROR: Could not find model file: '{MODEL_FILE_NAME}'")
    st.stop()

# 3. LOAD MODEL
model = joblib.load(MODEL_FILE_NAME)

# 4. SIDEBAR SETTINGS
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Select Mode:", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

# MULTI-CONTACT SETTINGS
st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
enable_sms = st.sidebar.checkbox("Enable SMS Alerts", value=True)
st.sidebar.caption("Enter up to 3 numbers to alert:")
phone_1 = st.sidebar.text_input("Contact 1 (Primary):", "+919999999999")
phone_2 = st.sidebar.text_input("Contact 2 (Family):", "")
phone_3 = st.sidebar.text_input("Contact 3 (Authorities):", "")

# ==========================================
# 🆘 SOS BUTTON LOGIC
# ==========================================
st.sidebar.divider()
st.sidebar.header("🆘 Emergency Panic Button")

# 8. SMS FUNCTION (Used by the SOS Button)
def send_sms_alert(phone, location, pressure):
    try:
        if "YOUR_TWILIO" in TWILIO_SID: return "SIMULATION"
        client = Client(TWILIO_SID, TWILIO_AUTH)
        message = client.messages.create(
            body=f"🚨 SOS! EMERGENCY ALERT from Cyclone Predictor. Help needed at {location}. Pressure: {pressure}hPa. This is an urgent SOS request.",
            from_=TWILIO_PHONE,
            to=phone
        )
        return "SENT"
    except Exception as e:
        return f"ERROR: {str(e)}"

# The pressable SOS Button
if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    # This block executes immediately when the button is pressed
    phone_list = [p for p in [phone_1, phone_2, phone_3] if p and len(p) > 5]
    
    if not phone_list:
        st.sidebar.warning("⚠️ No emergency contacts found. Please enter a phone number.")
    else:
        with st.sidebar:
            with st.spinner("Sending SOS alerts..."):
                for phone in phone_list:
                    # We use the current location name and pressure from the session state
                    # These values are updated by the Live API or Manual slider below
                    status = send_sms_alert(phone, st.session_state.get('loc_name', 'Unknown'), st.session_state.get('cur_pres', 'Unknown'))
                    
                    if status == "SENT":
                        st.success(f"✅ SOS sent to {phone}")
                    elif status == "SIMULATION":
                        st.info(f"📲 [Simulation] SOS triggered for {phone}")
                    else:
                        st.error(f"❌ Failed to send to {phone}: {status}")

# ==========================================
# (Rest of the original Logic)
# ==========================================

# Default Values
lat, lon, pres = 17.7, 83.3, 1012.0 
location_name = "Vizag (Default)"
is_vizag = True 

# 5. LIVE FETCH LOGIC
if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("Enter City Name:", "Visakhapatnam")
    is_vizag = "visakhapatnam" in city.lower() or "vizag" in city.lower()
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        lat, lon, pres = data['coord']['lat'], data['coord']['lon'], data['main']['pressure']
        location_name = f"{data['name']}, {data['sys']['country']}"
        st.sidebar.success("Live Data Fetched!")

# 6. MANUAL SIMULATION LOGIC
elif mode == "🎛️ Manual Simulation":
    st.sidebar.divider()
    location_name = "Custom Simulation"
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 960)
    is_vizag = 17.5 < lat < 18.0 and 83.0 < lon < 83.5

# Store current state for the SOS button
st.session_state['loc_name'] = location_name
st.session_state['cur_pres'] = pres

# 7. PREDICTION LOGIC
features = [[lat, lon, pres]]
prediction_index = model.predict(features)[0]
confidence = np.max(model.predict_proba(features)[0]) * 100
grades = {0: ("🟢 SAFE", "No threat."), 1: ("🟡 DEPRESSION", "Watch."), 2: ("🟠 STORM", "Warning!"), 3: ("🔴 CYCLONE", "DANGER!")}
label, desc = grades[prediction_index]

# 9. DASHBOARD LAYOUT
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {location_name}")
    st.metric("Pressure", f"{pres} hPa")
    if prediction_index >= 2:
        st.error(f"## {label}")
    else:
        st.success(f"## {label}")
    st.write(f"**Confidence:** {confidence:.1f}%")

with col2:
    st.subheader("🛰️ Live Satellite Risk Map")
    m = folium.Map(location=[lat, lon], zoom_start=11)
    st_folium(m, width=800, height=500)