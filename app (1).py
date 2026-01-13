import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# 🔑 CONFIGURATION (Using Secrets for Security)
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Prevents app crash if secrets are missing
try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
except Exception:
    st.error("❌ ERROR: Twilio Secrets not found in Dashboard!")
    st.info("Please go to App Settings > Secrets and add TWILIO_SID, TWILIO_AUTH, and TWILIO_PHONE.")
    st.stop()

CSV_FILE_NAME = 'ibtracs.NI.list.v04r01.zip' 
MODEL_FILE_NAME = 'cyclone_model.joblib'

# ==========================================
# 🆘 EMERGENCY ALERT FUNCTION
# ==========================================
def trigger_emergency_alerts(phone, location, lat, lon):
    """Sends SMS with Map link and makes a Hindi Voice Call"""
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        map_url = f"https://www.google.com/maps?q={lat},{lon}"
        
        # 1. Send SMS
        client.messages.create(
            body=f"🚨 SOS CYCLONE ALERT! User needs help. Location: {map_url}",
            from_=TWILIO_PHONE,
            to=phone
        )
        
        # 2. Trigger Hindi Voice Call
        client.calls.create(
            twiml=f'''
            <Response>
                <Say language="hi-IN">Emergency alert! Cyclone khatra detected. User ki location SMS kar di gayi hai.</Say>
            </Response>
            ''',
            from_=TWILIO_PHONE,
            to=phone
        )
        return "SENT"
    except Exception as e:
        return f"ERROR: {str(e)}"

# 1. PAGE CONFIG
st.set_page_config(page_title="Cyclone Predictor & SOS", page_icon="🌪️", layout="wide")
st.title("🌪️ North Indian Ocean Cyclone Predictor & SOS Hub")

# 2. LOAD MODEL
model = joblib.load(MODEL_FILE_NAME)

# 3. SIDEBAR SOS & CONTACTS
st.sidebar.header("🆘 Web SOS Panic Button")
# Get real-time GPS from browser
location_data = streamlit_geolocation() 
phone_1 = st.sidebar.text_input("Primary Contact (+91...):", "+919999999999")
phone_2 = st.sidebar.text_input("Secondary Contact:", "")

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    if location_data['latitude']:
        with st.spinner("Initiating alerts..."):
            for p in [phone_1, phone_2]:
                if p and len(p) > 5:
                    trigger_emergency_alerts(p, "User Location", location_data['latitude'], location_data['longitude'])
            st.sidebar.success("✅ Help is on the way! Alerts sent.")
    else:
        st.sidebar.warning("📍 Please allow location access in your browser.")

st.sidebar.divider()
mode = st.sidebar.radio("Data Mode:", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

# (Rest of your original weather fetching and map logic follows...)