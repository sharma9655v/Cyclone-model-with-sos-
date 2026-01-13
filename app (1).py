import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
# Library to get GPS location from the browser
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
# Go to twilio.com to get these keys
TWILIO_SID = "AC_YOUR_TWILIO_SID_HERE" 
TWILIO_AUTH = "YOUR_TWILIO_AUTH_TOKEN_HERE"
TWILIO_PHONE = "+1234567890"

CSV_FILE_NAME = 'ibtracs.NI.list.v04r01.zip' 
MODEL_FILE_NAME = 'cyclone_model.joblib'
# ==========================================

# 1. PAGE CONFIG
st.set_page_config(page_title="Cyclone Predictor & SOS", page_icon="🌪️", layout="wide")
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

# EMERGENCY CONTACTS
st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
enable_sms = st.sidebar.checkbox("Enable Automated Alerts", value=True)
st.sidebar.caption("Enter numbers to alert (Include country code, e.g., +91):")
phone_1 = st.sidebar.text_input("Contact 1 (Primary):", "+919999999999")
phone_2 = st.sidebar.text_input("Contact 2 (Family):", "")
phone_3 = st.sidebar.text_input("Contact 3 (Authorities):", "")

# ==========================================
# 🆘 WEB SOS SYSTEM LOGIC
# ==========================================
st.sidebar.divider()
st.sidebar.header("🆘 Web SOS Panic Button")
st.sidebar.write("Get location and trigger emergency SMS & Call.")

# This component asks the browser for GPS coordinates
location = streamlit_geolocation()

def trigger_sos_system(phone, lat, lon):
    """Sends SMS with Map link and makes a Hindi Voice Call"""
    try:
        if "YOUR_TWILIO" in TWILIO_SID: return "SIMULATION"
        client = Client(TWILIO_SID, TWILIO_AUTH)
        map_url = f"http://google.com/maps/place/{lat},{lon}"
        
        # 1. Send SMS Alert
        client.messages.create(
            body=f"🚨 SOS CYCLONE ALERT! Help needed at location: {map_url}",
            from_=TWILIO_PHONE,
            to=phone
        )
        
        # 2. Trigger Voice Call with Hindi Text-to-Speech
        client.calls.create(
            twiml=f'''
            <Response>
                <Say language="hi-IN">Emergency alert! Cyclone khatra detected. Sahayata bheji ja rahi hai.</Say>
            </Response>
            ''',
            from_=TWILIO_PHONE,
            to=phone
        )
        return "SENT"
    except Exception as e:
        return f"ERROR: {str(e)}"

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    if location and location['latitude']:
        with st.spinner("Initiating emergency signals..."):
            contact_list = [phone_1, phone_2, phone_3]
            for p in contact_list:
                if p and len(p) > 5:
                    status = trigger_sos_system(p, location['latitude'], location['longitude'])
                    if status == "SENT": st.sidebar.success(f"✅ Call & SMS sent to {p}")
                    elif status == "SIMULATION": st.sidebar.info(f"📲 [Simulation] SOS for {p}")
    else:
        st.sidebar.warning("📍 Please allow 'Location Access' in your browser first.")

# ==========================================
# PREDICTION & MAP LOGIC
# ==========================================
# (Rest of your original logic for live fetch, prediction, and mapping)
lat_val, lon_val, pres_val = 17.7, 83.3, 1012.0 
location_name = "Vizag (Default)"
is_vizag = True 

if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("Enter City Name:", "Visakhapatnam")
    is_vizag = "visakhapatnam" in city.lower() or "vizag" in city.lower()
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        lat_val, lon_val, pres_val = data['coord']['lat'], data['coord']['lon'], data['main']['pressure']
        location_name = f"{data['name']}, {data['sys']['country']}"
        st.sidebar.success("Live Data Fetched!")

elif mode == "🎛️ Manual Simulation":
    lat_val = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon_val = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres_val = st.sidebar.slider("Pressure (hPa)", 900, 1020, 960)
    is_vizag = 17.5 < lat_val < 18.0 and 83.0 < lon_val < 83.5

# AI Analysis
features = [[lat_val, lon_val, pres_val]]
prediction_index = model.predict(features)[0]
confidence = np.max(model.predict_proba(features)[0]) * 100
grades = {0: ("🟢 SAFE", "No threat."), 1: ("🟡 DEPRESSION", "Watch."), 2: ("🟠 STORM", "Warning!"), 3: ("🔴 CYCLONE", "DANGER!")}
label, desc = grades[prediction_index]

# Dashboard Display
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {location_name}")
    st.metric("Pressure", f"{pres_val} hPa")
    if prediction_index >= 2:
        st.error(f"## {label}")
    else:
        st.success(f"## {label}")
    st.write(f"**Confidence:** {confidence:.1f}%")

with col2:
    st.subheader("🛰️ Live Satellite Risk Map")
    m = folium.Map(location=[lat_val, lon_val], zoom_start=11)
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)
    st_folium(m, width=800, height=500)