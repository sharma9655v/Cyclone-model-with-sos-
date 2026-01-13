import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
# NEW: Library to get GPS location from the browser
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

# MULTI-CONTACT SETTINGS
st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
enable_sms = st.sidebar.checkbox("Enable SMS Alerts", value=True)
st.sidebar.caption("Enter numbers to alert (Include +91 for India):")
phone_1 = st.sidebar.text_input("Contact 1 (Primary):", "+919999999999")
phone_2 = st.sidebar.text_input("Contact 2 (Family):", "")
phone_3 = st.sidebar.text_input("Contact 3 (Authorities):", "")

# ==========================================
# 🆘 NEW: WEB SOS SYSTEM LOGIC
# ==========================================
st.sidebar.divider()
st.sidebar.header("🆘 Web SOS Panic Button")
st.sidebar.write("Click below to send your GPS location and trigger an emergency call.")

# This component asks the user for GPS permission
location_data = streamlit_geolocation()

def trigger_emergency_system(phones, lat, lon):
    """Sends SMS with Map and makes a Hindi Voice Call"""
    map_link = f"https://www.google.com/maps?q={lat},{lon}"
    results = []
    
    if "YOUR_TWILIO" in TWILIO_SID:
        st.sidebar.warning("Twilio keys not set. Running in Simulation mode.")
        return ["SIMULATED"]

    client = Client(TWILIO_SID, TWILIO_AUTH)
    
    for p in phones:
        if p and len(p) > 5:
            try:
                # 1. Send SMS Alert
                client.messages.create(
                    body=f"🚨 SOS CYCLONE ALERT! User needs help. Location: {map_link}",
                    from_=TWILIO_PHONE,
                    to=p
                )
                
                # 2. Make Voice Call with Hindi Message
                client.calls.create(
                    twiml=f'''
                    <Response>
                        <Say language="hi-IN">Emergency alert! Cyclone khatra detected. User ki location SMS kar di gayi hai. Kripya turant sahayata bheje.</Say>
                    </Response>
                    ''',
                    from_=TWILIO_PHONE,
                    to=p
                )
                results.append(f"Sent to {p}")
            except Exception as e:
                results.append(f"Error for {p}: {str(e)}")
    return results

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    if location_data['latitude']:
        with st.spinner("Sending emergency alerts..."):
            contact_list = [phone_1, phone_2, phone_3]
            responses = trigger_emergency_system(contact_list, location_data['latitude'], location_data['longitude'])
            for r in responses:
                st.sidebar.success(r)
    else:
        st.sidebar.error("📍 Error: Please allow 'Location Access' in your browser.")

# ==========================================
# (REST OF YOUR ORIGINAL LOGIC)
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
    location_name = "Custom Simulation"
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 960)
    is_vizag = 17.5 < lat < 18.0 and 83.0 < lon < 83.5

# 7. PREDICTION LOGIC
features = [[lat, lon, pres]]
prediction_index = model.predict(features)[0]
confidence = np.max(model.predict_proba(features)[0]) * 100

grades = {0: ("🟢 SAFE", "No threat."), 1: ("🟡 DEPRESSION", "Watch."), 2: ("🟠 STORM", "Warning!"), 3: ("🔴 CYCLONE", "DANGER!")}
label, desc = grades[prediction_index]

# 8. ORIGINAL SMS FUNCTION (Modified to use Twilio keys)
def send_sms_alert(phone, location, pressure):
    try:
        if "YOUR_TWILIO" in TWILIO_SID: return "SIMULATION"
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(
            body=f"🚨 CYCLONE ALERT! High danger in {location}. Pressure: {pressure}hPa.",
            from_=TWILIO_PHONE, to=phone
        )
        return "SENT"
    except: return "ERROR"

# 9. DASHBOARD LAYOUT
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {location_name}")
    st.metric("Pressure", f"{pres} hPa")
    st.metric("Coordinates", f"{lat:.2f}°N, {lon:.2f}°E")
    st.divider()
    if prediction_index >= 2:
        st.error(f"## {label}")
        if is_vizag:
            st.error("🚨 VIZAG EMERGENCY PROTOCOL")
            if enable_sms:
                for p in [phone_1, phone_2, phone_3]:
                    if p: send_sms_alert(p, location_name, pres)
    elif prediction_index == 1: st.warning(f"## {label}")
    else: st.success(f"## {label}")
    st.write(f"**Confidence:** {confidence:.1f}%")

with col2:
    st.subheader("🛰️ Live Satellite Risk Map")
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles=None)
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satellite').add_to(m)

    if is_vizag and prediction_index >= 2:
        lats, lons = np.meshgrid(np.linspace(17.60, 17.72, 25), np.linspace(83.15, 83.35, 25))
        for la, lo in zip(lats.flatten(), lons.flatten()):
            coast = (0.7 * (la - 17.60)) + 83.22
            color = '#ff0000' if lo > coast else '#00ff00'
            folium.Circle(location=[la, lo], radius=120, color=color, fill=True).add_to(m)
    
    st_folium(m, width=800, height=500)