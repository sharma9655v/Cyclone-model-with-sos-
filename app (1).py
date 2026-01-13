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
# Replace these with your actual keys
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
TWILIO_SID = "AC_YOUR_TWILIO_SID_HERE"
TWILIO_AUTH = "YOUR_TWILIO_AUTH_TOKEN_HERE"
TWILIO_PHONE = "+1234567890"

# Files required in your repository
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

# Default Values
lat, lon, pres = 17.7, 83.3, 1012.0 
location_name = "Vizag (Default)"
is_vizag = True 
api_status = "Not Connected"

# 5. LIVE FETCH LOGIC
if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("Enter City Name:", "Visakhapatnam")
    
    if "visakhapatnam" in city.lower() or "vizag" in city.lower():
        is_vizag = True
    else:
        is_vizag = False

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        lat = data['coord']['lat']
        lon = data['coord']['lon']
        pres = data['main']['pressure']
        location_name = f"{data['name']}, {data['sys']['country']}"
        api_status = "✅ Connected to OpenWeatherMap"
        st.sidebar.success("Live Data Fetched!")
    elif response.status_code == 401:
        st.sidebar.error("⏳ API Key not active yet. Please wait.")
    else:
        st.sidebar.error("❌ City not found. Check spelling.")

# 6. MANUAL SIMULATION LOGIC
elif mode == "🎛️ Manual Simulation":
    st.sidebar.divider()
    location_name = "Custom Simulation"
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, 17.7)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, 83.3)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, 960)
    
    if 17.5 < lat < 18.0 and 83.0 < lon < 83.5:
        is_vizag = True
    else:
        is_vizag = False

# 7. PREDICTION LOGIC
features = [[lat, lon, pres]]
prediction_index = model.predict(features)[0]
confidence = np.max(model.predict_proba(features)[0]) * 100

grades = {
    0: ("🟢 SAFE", "No threat detected."),
    1: ("🟡 DEPRESSION", "Watch required."),
    2: ("🟠 STORM", "Warning issued."),
    3: ("🔴 CYCLONE", "High danger!")
}
label, desc = grades[prediction_index]

# 8. SMS FUNCTION
def send_sms_alert(phone, location, pressure):
    try:
        if "YOUR_TWILIO" in TWILIO_SID: return "SIMULATION"
        client = Client(TWILIO_SID, TWILIO_AUTH)
        message = client.messages.create(
            body=f"🚨 CYCLONE ALERT! High danger in {location}. Pressure: {pressure}hPa. Evacuate!",
            from_=TWILIO_PHONE,
            to=phone
        )
        return "SENT"
    except Exception as e:
        return f"ERROR: {str(e)}"

# 9. DASHBOARD LAYOUT
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader(f"📍 {location_name}")
    if mode == "📡 Live Weather (API)":
        st.caption(api_status)
    
    st.metric("Pressure", f"{pres} hPa")
    st.metric("Coordinates", f"{lat:.2f}°N, {lon:.2f}°E")
    
    st.divider()
    st.subheader("AI Analysis")
    if prediction_index >= 2:
        st.error(f"## {label}")
        
        # SMS Logic
        if is_vizag:
            st.error("🚨 VIZAG EMERGENCY PROTOCOL ACTIVATED")
            if enable_sms and prediction_index == 3:
                phone_list = [phone_1, phone_2, phone_3]
                for phone in phone_list:
                    if phone and len(phone) > 5:
                        status = send_sms_alert(phone, location_name, pres)
                        if status == "SENT": st.toast(f"📲 Alert sent to {phone}", icon="✅")
                        elif status == "SIMULATION": st.info(f"📲 [SIMULATION] SMS sent to {phone}")
    
    elif prediction_index == 1:
        st.warning(f"## {label}")
    else:
        st.success(f"## {label}")
    st.write(f"**Confidence:** {confidence:.1f}%")
    st.info(desc)

with col2:
    # --- 🛰️ SATELLITE MAP LOGIC ---
    st.subheader("🛰️ Live Satellite Risk Map")
    
    # 1. Base Map (Satellite)
    m = folium.Map(location=[lat, lon], zoom_start=11, tiles=None)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # 2. Add Risk Grid (Vizag Emergency)
    if is_vizag and prediction_index >= 2:
        lat_min, lat_max = 17.60, 17.72
        lon_min, lon_max = 83.15, 83.35
        
        lats = np.linspace(lat_min, lat_max, 25)
        lons = np.linspace(lon_min, lon_max, 25)
        grid_lats, grid_lons = np.meshgrid(lats, lons)
        flat_lats, flat_lons = grid_lats.flatten(), grid_lons.flatten()
        
        for la, lo in zip(flat_lats, flat_lons):
            coast_line = (0.7 * (la - 17.60)) + 83.22
            if lo > coast_line: color = '#ff0000' # Red
            elif lo > (coast_line - 0.02): color = '#ffa500' # Orange
            else: color = '#00ff00' # Green
            
            folium.Circle(
                location=[la, lo],
                radius=120,
                color=color,
                fill=True,
                fill_opacity=0.6
            ).add_to(m)
            
    # 3. Add Historical Data (Global Blue/Red Dots)
    else:
        @st.cache_data
        def load_map_data():
            if not os.path.exists(CSV_FILE_NAME): return None
            try:
                df = pd.read_csv(CSV_FILE_NAME, header=None, skiprows=[1], usecols=[8, 9, 10], names=['lat', 'lon', 'wind'], low_memory=False)
                df = df.apply(pd.to_numeric, errors='coerce').dropna()
                if len(df) > 1000: df = df.sample(1000)
                return df
            except: return None

        history_df = load_map_data()
        if history_df is not None:
            for _, row in history_df.iterrows():
                color = '#ff0000' if row['wind'] >= 64 else '#0000ff'
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=2,
                    color=color,
                    fill=True
                ).add_to(m)

    # Render Map
    st_folium(m, width=800, height=500)