import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
from twilio.rest import Client
import folium
from streamlit_folium import st_folium

# ==========================================
# 🔑 CONFIGURATION (TWILIO & WEATHER)
# ==========================================
# Get your OpenWeatherMap API key from https://openweathermap.org/api
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Twilio Credentials (Verify numbers in Console to avoid Error 400)
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE = "+15075195618"

MODEL_FILE = "cyclone_model.joblib"

st.set_page_config(page_title="Cyclone SOS Dashboard", page_icon="🌪️", layout="wide")

# ==========================================
# 🆘 SOS FUNCTION (SMS + HINDI VOICE)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        # SMS Alert
        client.messages.create(
            body=f"🚨 SOS ALERT: {label} detected at {location}. Pressure: {pressure} hPa. Follow safety steps!",
            from_=TWILIO_PHONE, to=target_phone
        )
        # Hindi Voice Call
        call_msg = f'<Response><Say language="hi-IN">Saavdhan! {location} mein chakravaat ka khatra hai.</Say></Response>'
        client.calls.create(twiml=call_msg, to=target_phone, from_=TWILIO_PHONE)
        return "SUCCESS"
    except Exception as e:
        return str(e)

# ==========================================
# 📊 SIDEBAR & DATA FETCHING
# ==========================================
st.sidebar.header("Settings")
city = st.sidebar.text_input("📍 Your City", "Visakhapatnam")
p1 = st.sidebar.text_input("Emergency Contact 1", "+917678495189")

# --- LIVE WEATHER DATA FETCH ---
url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
try:
    res = requests.get(url).json()
    lat, lon = res["coord"]["lat"], res["coord"]["lon"]
    pres = res["main"]["pressure"]
    wind = res["wind"]["speed"]
    loc_display = res["name"]
except:
    st.error("Could not fetch live data. Please check your API key.")
    st.stop()

# ==========================================
# 🔮 PREDICTION & DASHBOARD
# ==========================================
model = joblib.load(MODEL_FILE)
# Prediction based on live Pressure, Latitude, and Longitude
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
current_status = labels[prediction_idx]

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Pressure", f"{pres} hPa")
    st.metric("Wind Speed", f"{wind} m/s")
    st.markdown(f"### Current Status: {current_status}")
    
    # TRIGGER SOS BUTTON
    if st.button("🚨 TRIGGER SOS NOW", use_container_width=True, type="primary"):
        with st.spinner("Sending Alerts..."):
            status = trigger_sos(p1, loc_display, pres, current_status)
            if status == "SUCCESS": st.success("Alert Sent!")
            else: st.error(f"Error: {status}")

with col2:
    # 2D Map with Warning Circle
    m = folium.Map(location=[lat, lon], zoom_start=8)
    active_color = ["#00FF00", "#FFFF00", "#FFA500", "#FF0000"][prediction_idx]
    folium.Circle(location=[lat, lon], radius=20000, color=active_color, fill=True).add_to(m)
    folium.Marker([lat, lon]).add_to(m)
    st_folium(m, width=700, height=400)

# ==========================================
# 📋 SURVIVAL GUIDE
# ==========================================
st.divider()
st.header("🩹 Cyclone Survival Guide")
t1, t2, t3 = st.tabs(["🕒 Phase 1: Preparation", "🌪️ Phase 2: During Storm", "🏠 Phase 3: Recovery"])
with t1: st.write("✅ Charge phones. ✅ Pack food/water. ✅ Secure loose items.")
with t2: st.write("🚨 Stay indoors. 🚨 Stay away from windows. 🚨 Turn off gas/power.")
with t3: st.write("✅ Wait for 'All Clear'. ✅ Avoid fallen wires. ✅ Check house for damage.")