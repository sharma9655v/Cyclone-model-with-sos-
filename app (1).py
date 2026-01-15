import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import pydeck as pdk
from datetime import datetime

# ==========================================
# 🔑 CONFIGURATION (2 TWILIO ACCOUNTS)
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Account 1 Credentials
TWILIO_SID_1 = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH_1 = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE_1 = "+15075195618"

# Account 2 Credentials (Backup)
TWILIO_SID_2 = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_2 = "6460cb8dfe71e335741bb20bc14c452a"
TWILIO_PHONE_2 = "+14176076960"

MODEL_FILE = "cyclone_model.joblib"

# Check if at least one account is configured correctly
SIMULATION_MODE = "YOUR_PRIMARY" in TWILIO_SID_1

st.set_page_config(page_title="3D Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🆘 SOS FUNCTION (DUAL ACCOUNT FAILOVER)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    if SIMULATION_MODE:
        return "SIMULATION"
    
    accounts = [
        {"sid": TWILIO_SID_1, "token": TWILIO_AUTH_1, "from": TWILIO_PHONE_1},
        {"sid": TWILIO_SID_2, "token": TWILIO_AUTH_2, "from": TWILIO_PHONE_2}
    ]
    
    last_error = ""
    for acc in accounts:
        try:
            client = Client(acc["sid"], acc["token"])
            
            # 1. SMS Alert (English)
            client.messages.create(
                body=f"🚨 SOS: Cyclone Risk Detected!\nStatus: {label}\nLocation: {location}\nPressure: {pressure} hPa",
                from_=acc["from"],
                to=target_phone
            )
            
            # 2. Voice Alert (Hindi)
            call_content = f'<Response><Say language="hi-IN">Saavdhan! {location} mein chakravaat ka khatra hai. Kripya surakshit sthaan par jaye.</Say></Response>'
            client.calls.create(twiml=call_content, to=target_phone, from_=acc["from"])
            
            return "SUCCESS" 
        except Exception as e:
            last_error = str(e)
            continue 
            
    return last_error

# ==========================================
# 🌪️ MAIN APP CONTENT
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

try:
    model = joblib.load(MODEL_FILE)
except Exception as e:
    st.error(f"Failed to load model: {e}")
    st.stop()

# ==========================================
# 📊 SIDEBAR (SOS Button & Contacts)
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
p1 = st.sidebar.text_input("Primary Contact", "+917678495189")
p2 = st.sidebar.text_input("Family Contact", "+918130631551")

# --- DATA ACQUISITION ---
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
    except: st.sidebar.warning("API Error. Using defaults.")
else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012)
    loc_display = "Simulation Area"

# --- PREDICTION ---
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
current_status = labels[prediction_idx]

# --- SIDEBAR SOS BUTTON ---
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS NOW", use_container_width=True, type="primary"):
    targets = [p for p in [p1, p2] if len(p) > 5]
    if not targets:
        st.sidebar.warning("Please enter a valid phone number.")
    else:
        for t in targets:
            with st.sidebar.spinner(f"Sending to {t}..."):
                status = trigger_sos(t, loc_display, pres, current_status)
                if status == "SUCCESS": st.sidebar.success(f"✅ Sent to {t}")
                else: st.sidebar.error(f"Error: {status}")

# ==========================================
# 🌍 3D DASHBOARD & PYDECK MAP
# ==========================================
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Atmospheric Pressure", f"{pres} hPa")
    st.markdown(f"### Current Status: {current_status}")
    if prediction_idx >= 2:
        st.warning("⚠️ HIGH RISK DETECTED!")

with col2:
    # 3D Coloring Logic (RGBA)
    colors = [
        [0, 255, 0, 160],   # Safe - Green
        [255, 255, 0, 160], # Depression - Yellow
        [255, 165, 0, 160], # Storm - Orange
        [255, 0, 0, 180]    # Cyclone - Red
    ]
    active_color = colors[prediction_idx]

    # Map state with 45-degree tilt for 3D effect
    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=9, pitch=45)
    
    # Layer 1: Highlighted circular boundary
    boundary_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": lat, "lon": lon}]),
        get_position="[lon, lat]",
        get_color=active_color,
        get_radius=15000, # 15km boundary highlight
    )
    
    # Layer 2: 3D Pillar indicating intensity
    pillar_layer = pdk.Layer(
        "ColumnLayer",
        data=pd.DataFrame([{"lat": lat, "lon": lon, "h": float((4 - prediction_idx) * 3500), "status": current_status}]),
        get_position="[lon, lat]",
        get_elevation="h",
        elevation_scale=1,
        radius=3000,
        get_fill_color=active_color,
        extruded=True,
        pickable=True
    )

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/dark-v10',
        initial_view_state=view_state,
        layers=[boundary_layer, pillar_layer],
        tooltip={"text": "Location: {status}"}
    ))