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
# 🔑 CONFIGURATION (2 TWILIO ACCOUNTS)
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Account 1 Credentials
TWILIO_SID_1 = "ACc9b9941c778de30e2ed7ba57f87cdfbc" 
TWILIO_AUTH_1 = "3cb1dfcb6a9a3cae88f4eff47e9458df"
TWILIO_PHONE_1 = "+15075195618"

# Account 2 Credentials (Backup)
TWILIO_SID_2 = "ACa12e602647785572ebaf765659d26d23"
TWILIO_AUTH_2 = "26210979738809eaf59a678e98fe2c0f"
TWILIO_PHONE_2 = "+14176076960"

MODEL_FILE = "cyclone_model.joblib"

# Check if at least one account is configured
SIMULATION_MODE = "YOUR_PRIMARY" in TWILIO_SID_1

st.set_page_config(page_title="Cyclone Predictor & SOS", page_icon="🌪️", layout="wide")

# ==========================================
# 🔐 SESSION INITIALIZATION
# ==========================================
if "loc_name" not in st.session_state:
    st.session_state.loc_name = "Unknown"
if "cur_pres" not in st.session_state:
    st.session_state.cur_pres = 1012

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
p1 = st.sidebar.text_input("Primary Contact", "+919999999999")
p2 = st.sidebar.text_input("Family Contact", "+91XXXXXXXXXX")

# --- INTERACTIVE CHECKLIST ---
st.sidebar.divider()
st.sidebar.subheader("✅ Readiness Checklist")
kit = st.sidebar.checkbox("Emergency Kit Ready")
charge = st.sidebar.checkbox("Phone/Powerbank Charged")
if kit and charge:
    st.sidebar.success("Preparedness Level: High")

# --- WEATHER LOGIC ---
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
    except: pass
else:
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 1012)
    loc_display = "Simulation Area"

st.session_state.loc_name = loc_display
st.session_state.cur_pres = pres

# Run Prediction
labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
current_status = labels[prediction_idx]

# --- SOS BUTTON IN SIDEBAR ---
st.sidebar.divider()
if st.sidebar.button("🚨 TRIGGER SOS NOW", use_container_width=True, type="primary"):
    targets = [p for p in [p1, p2] if len(p) > 5]
    if not targets:
        st.sidebar.warning("Please enter a phone number.")
    else:
        for t in targets:
            with st.sidebar.spinner(f"Sending to {t}..."):
                status = trigger_sos(t, loc_display, pres, current_status)
                if status == "SUCCESS": st.sidebar.success(f"✅ Sent to {t}")
                else: st.sidebar.error(f"Error {t}: {status}")

# ==========================================
# 🌍 DASHBOARD DISPLAY
# ==========================================
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Pressure", f"{pres} hPa")
    st.markdown(f"### Current Status: {current_status}")
    if prediction_idx >= 2:
        st.error("🚨 DANGER: Move to a safe location immediately!")
    elif prediction_idx == 1:
        st.warning("⚠️ ALERT: High winds expected. Be prepared.")

with col2:
    hex_colors = ["#00FF00", "#FFFF00", "#FFA500", "#FF0000"]
    active_color = hex_colors[prediction_idx]
    
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker([lat, lon], popup=loc_display).add_to(m)
    
    # Highlight the search area with a colored boundary
    folium.Circle(
        location=[lat, lon],
        radius=15000, # 15km
        color=active_color,
        fill=True,
        fill_opacity=0.4
    ).add_to(m)
    
    st_folium(m, width=700, height=450)

# ==========================================
# 📋 COMPREHENSIVE SURVIVAL GUIDE
# ==========================================
st.divider()
st.header("🩹 Advanced Cyclone Survival Guide")



tab1, tab2, tab3 = st.tabs(["🕒 Phase 1: Preparation", "🌪️ Phase 2: During Storm", "🏠 Phase 3: Recovery"])

with tab1:
    st.markdown("""
    **Before the cyclone hits:**
    * **🌳 Structural Safety:** Trim tree branches near your house or power lines.
    * **🧴 Water Storage:** Fill clean containers with at least 5-7 days' worth of drinking water.
    * **📄 Documents:** Put ID, property papers, and insurance in a **waterproof bag**.
    * **🧹 Clean Up:** Move loose outdoor items (trash bins, chairs) inside.
    """)

with tab2:
    st.markdown("""
    **While the storm is active:**
    * **🚪 Stay Indoors:** Do not go out under any circumstances.
    * **🛡️ Safe Spot:** Stay in the strongest part of the house (hallway or small bathroom) away from glass windows.
    * **🔌 Electricity:** Switch off the main power supply and gas.
    * **⚠️ The Eye:** If the wind stops suddenly, **do not go out**. The wind will return shortly.
    """)



with tab3:
    st.markdown("""
    **After the storm has passed:**
    * **📻 Listen:** Wait for official 'All Clear' news from authorities.
    * **⚡ Danger:** Stay away from fallen electric poles and broken wires.
    * **🧤 Clean Up:** Wear strong shoes and gloves when clearing debris to avoid injury.
    """)