import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
# This gets the GPS data from the user's browser
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# 🔑 SECURE CONFIGURATION (Uses st.secrets)
# ==========================================
# No more hardcoded keys here! Pulling from Streamlit's secure vault
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
except KeyError:
    st.error("❌ Twilio Secrets not found! Please add them to your Streamlit Cloud settings.")
    st.stop()

MODEL_FILE_NAME = 'cyclone_model.joblib'
CSV_FILE_NAME = 'ibtracs.NI.list.v04r01.zip'
# ==========================================

st.set_page_config(page_title="Cyclone SOS Predictor", page_icon="🌪️", layout="wide")
st.title("🌪️ North Indian Ocean Cyclone Predictor")

# 1. LOAD MODEL
if not os.path.exists(MODEL_FILE_NAME):
    st.error(f"❌ Model file '{MODEL_FILE_NAME}' missing!")
    st.stop()
model = joblib.load(MODEL_FILE_NAME)

# 2. SIDEBAR - EMERGENCY CONTACTS
st.sidebar.header("🚨 Emergency Settings")
phone_1 = st.sidebar.text_input("Primary Contact (e.g. +91...):", "+919999999999")
phone_2 = st.sidebar.text_input("Secondary Contact:", "")
enable_sms = st.sidebar.checkbox("Enable Auto-SMS on Danger", value=True)

# 3. WEB SOS SYSTEM (HINDI VOICE)
st.sidebar.divider()
st.sidebar.header("🆘 Web SOS Panic Button")
st.sidebar.info("Click 'Allow' on the browser popup to share your location.")

# Component to capture real-time GPS
location = streamlit_geolocation()

def trigger_sos_alerts(lat, lon):
    """Triggers SMS and Hindi Voice Call via Twilio"""
    client = Client(TWILIO_SID, TWILIO_AUTH)
    map_url = f"https://www.google.com/maps?q={lat},{lon}"
    contacts = [p for p in [phone_1, phone_2] if p]
    
    for p in contacts:
        try:
            # 1. Send Emergency SMS
            client.messages.create(
                body=f"🚨 SOS CYCLONE! User needs help at location: {map_url}",
                from_=TWILIO_PHONE,
                to=p
            )
            # 2. Trigger Voice Call with Hindi Text-to-Speech
            client.calls.create(
                twiml=f'''
                <Response>
                    <Say language="hi-IN">Emergency alert! Cyclone khatra hai. Location aapko SMS kar di gayi hai. Kripya turant sahayata bheje.</Say>
                </Response>
                ''',
                from_=TWILIO_PHONE,
                to=p
            )
            st.toast(f"✅ Alerts sent to {p}")
        except Exception as e:
            st.error(f"Failed to alert {p}: {e}")

if st.sidebar.button("🚨 SEND SOS NOW", type="primary", use_container_width=True):
    if location and location.get('latitude'):
        trigger_sos_alerts(location['latitude'], location['longitude'])
    else:
        st.sidebar.warning("📍 Location not found. Please enable GPS in your browser.")

# 4. PREDICTION LOGIC (Your Original Weather Code)
st.sidebar.divider()
mode = st.sidebar.radio("Mode:", ["📡 Live API", "🎛️ Manual"])

lat, lon, pres = 17.7, 83.3, 1012.0 # Defaults
if mode == "📡 Live API":
    city = st.sidebar.text_input("City:", "Visakhapatnam")
    res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}")
    if res.status_code == 200:
        d = res.json()
        lat, lon, pres = d['coord']['lat'], d['coord']['lon'], d['main']['pressure']

# AI Prediction
prediction = model.predict([[lat, lon, pres]])[0]
grades = {0: "🟢 SAFE", 1: "🟡 DEPRESSION", 2: "🟠 STORM", 3: "🔴 CYCLONE"}

# 5. DASHBOARD DISPLAY
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("Pressure", f"{pres} hPa")
    status = grades[prediction]
    if prediction >= 2:
        st.error(f"## {status}")
    else:
        st.success(f"## {status}")

with col2:
    m = folium.Map(location=[lat, lon], zoom_start=10)
    folium.Marker([lat, lon], popup="Current Position").add_to(m)
    st_folium(m, width=700, height=400)