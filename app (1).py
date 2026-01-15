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
# 🔑 CONFIGURATION (TWILIO)
# ==========================================
# These should ideally be in st.secrets for safety
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
TWILIO_SID = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE = "+15075195618"

MODEL_FILE = "cyclone_model.joblib"

st.set_page_config(page_title="Cyclone SOS Dashboard", page_icon="🌪️", layout="wide")

# ==========================================
# 🆘 SOS FUNCTION (SMS + VOICE)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    try:
        # Numbers must be in E.164 format (+CountryCodeNumber)
        client = Client(TWILIO_SID, TWILIO_AUTH)
        
        # 1. Send SMS (English)
        client.messages.create(
            body=f"🚨 SOS ALERT: {label} detected at {location}. Pressure: {pressure} hPa. Take safety measures!",
            from_=TWILIO_PHONE,
            to=target_phone
        )
        
        # 2. Make Voice Call (Hindi Message)
        # TwiML instructs Twilio to speak the text
        call_msg = f'<Response><Say language="hi-IN">Saavdhan! {location} mein chakravaat ka khatra hai. Kripya surakshit sthaan par jaye.</Say></Response>'
        client.calls.create(twiml=call_msg, to=target_phone, from_=TWILIO_PHONE)
        
        return "SUCCESS"
    except Exception as e:
        # Error 400 often means unverified number; 401 means wrong SID/Auth
        return str(e)

# ==========================================
# 🌪️ MAIN APP
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

try:
    model = joblib.load(MODEL_FILE)
except Exception as e:
    st.error(f"Model file missing or corrupted: {e}")
    st.stop()

# ==========================================
# 📊 SIDEBAR
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
st.sidebar.caption("💡 Tip: Verify numbers in Twilio Console to avoid Error 400.")
p1 = st.sidebar.text_input("Primary Contact", "+917678495189")
p2 = st.sidebar.text_input("Family Contact", "+918130631551")

# SIDEBAR CHECKLIST
st.sidebar.divider()
st.sidebar.subheader("✅ Readiness Checklist")
kit = st.sidebar.checkbox("Emergency Kit Ready")
charge = st.sidebar.checkbox("Phone/Powerbank Charged")

# --- WEATHER DATA ---
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
    except:
        st.sidebar.warning("API check failed. Using defaults.")
else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012)
    loc_display = "Simulation"

# --- PREDICTION ---
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
current_status = labels[prediction_idx]

# --- SOS BUTTON ---
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS NOW", use_container_width=True, type="primary"):
    targets = [p for p in [p1, p2] if len(p) > 10]
    if not targets:
        st.sidebar.warning("Enter a valid number starting with +91")
    else:
        for t in targets:
            with st.sidebar.spinner(f"Contacting {t}..."):
                status = trigger_sos(t, loc_display, pres, current_status)
                if status == "SUCCESS":
                    st.sidebar.success(f"✅ Alert Sent to {t}")
                else:
                    st.sidebar.error(f"Failed {t}: {status}")

# ==========================================
# 🌍 2D DASHBOARD & MAP
# ==========================================
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Pressure", f"{pres} hPa")
    st.markdown(f"### Status: {current_status}")
    if prediction_idx >= 2:
        st.error("🚨 DANGER: Move to a safe location immediately!")

with col2:
    hex_colors = ["#00FF00", "#FFFF00", "#FFA500", "#FF0000"]
    active_color = hex_colors[prediction_idx]
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker([lat, lon], popup=loc_display).add_to(m)
    folium.Circle(
        location=[lat, lon],
        radius=15000,
        color=active_color,
        fill=True,
        fill_opacity=0.4
    ).add_to(m)
    st_folium(m, width=700, height=450)

# ==========================================
# 📋 SURVIVAL GUIDE SECTION
# ==========================================
st.divider()
st.header("🩹 Cyclone Survival Guide")
tab1, tab2, tab3 = st.tabs(["🕒 Phase 1: Preparation", "🌪️ Phase 2: During Storm", "🏠 Phase 3: Recovery"])

with tab1:
    st.markdown("* **🔋 Power:** Charge all phones and power banks.\n* **🎒 Go-Bag:** Keep water, snacks, and a torch ready.")
with tab2:
    st.markdown("* **🚪 Stay Indoors:** Shelter in a small room away from glass.\n* **🔌 Electricity:** Switch off main power and gas.")
with tab3:
    st.markdown("* **📻 Listen:** Wait for official 'All Clear' news.\n* **⚡ Danger:** Stay away from fallen poles and wires.")