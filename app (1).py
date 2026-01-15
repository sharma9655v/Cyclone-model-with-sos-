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
# Ensure these match your Twilio Console EXACTLY
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE = "+15075195618"

MODEL_FILE = "cyclone_model.joblib"

st.set_page_config(page_title="Cyclone SOS System", page_icon="🌪️", layout="wide")

# ==========================================
# 🆘 SOS FUNCTION (WITH ERROR DIAGNOSTICS)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    try:
        # Initialize Client
        client = Client(TWILIO_SID, TWILIO_AUTH)
        
        # 1. SEND SMS (English)
        # Note: target_phone must be in E.164 format (e.g., +91...)
        sms = client.messages.create(
            body=f"🚨 SOS ALERT: {label} at {location}. Pressure: {pressure} hPa. Please take cover!",
            from_=TWILIO_PHONE,
            to=target_phone
        )
        
        # 2. MAKE VOICE CALL (Hindi Message)
        # Twilio Trial accounts only support SMS verification for Caller IDs
        call_msg = f'<Response><Say language="hi-IN">Saavdhan! {location} mein chakravaat ka khatra hai. Kripya surakshit sthaan par jaye.</Say></Response>'
        call = client.calls.create(
            twiml=call_msg,
            to=target_phone,
            from_=TWILIO_PHONE
        )
        
        return "SUCCESS"
    except Exception as e:
        error_msg = str(e)
        if "21608" in error_msg or "unverified" in error_msg.lower():
            return "ERROR: Phone number is not VERIFIED in Twilio Console."
        elif "Authenticate" in error_msg:
            return "ERROR: Invalid Account SID or Auth Token."
        return error_msg

# ==========================================
# 🌪️ MAIN APP & SIDEBAR
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
# MUST VERIFY THESE AT: https://www.twilio.com/console/phone-numbers/verified
p1 = st.sidebar.text_input("Primary Contact (Verified)", "+917678495189")
p2 = st.sidebar.text_input("Family Contact (Verified)", "+918130631551")

# --- WEATHER & PREDICTION LOGIC ---
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
    except: st.sidebar.warning("Weather API unreachable.")
else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7); lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012); loc_display = "Simulation"

# Prediction
model = joblib.load(MODEL_FILE)
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
current_status = labels[prediction_idx]

# --- SOS BUTTON ---
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS NOW", use_container_width=True, type="primary"):
    targets = [p for p in [p1, p2] if len(p) > 10]
    for t in targets:
        with st.sidebar.spinner(f"Alerting {t}..."):
            status = trigger_sos(t, loc_display, pres, current_status)
            if status == "SUCCESS": st.sidebar.success(f"✅ Alert Sent to {t}")
            else: st.sidebar.error(f"{status}")

# ==========================================
# 🌍 MAP & SURVIVAL GUIDE
# ==========================================
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader(f"📍 {loc_display}"); st.metric("Pressure", f"{pres} hPa"); st.markdown(f"### Status: {current_status}")
with c2:
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Circle(location=[lat, lon], radius=15000, color="#FF0000", fill=True).add_to(m)
    st_folium(m, width=700, height=400)

st.divider()
st.header("🩹 Survival Guide")
with st.expander("📝 Critical Safety Steps"):
    st.write("1. **Charge Devices:** Keep phones at 100%.")
    st.write("2. **Stay Indoors:** Avoid windows during high winds.")
    st.write("3. **Emergency Kit:** Pack water, food, and a torch.")