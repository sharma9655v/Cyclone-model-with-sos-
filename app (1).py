import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
import folium
from streamlit_folium import st_folium

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"
MODEL_FILE = "cyclone_model.joblib"

st.set_page_config(page_title="2D Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🆘 SOS FUNCTION (TEXTBELT)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    try:
        payload = {
            'phone': target_phone,
            'message': f"🚨 SOS ALERT: {label}\nLocation: {location}\nPressure: {pressure} hPa",
            'key': 'textbelt', 
        }
        response = requests.post('https://textbelt.com/text', data=payload)
        result = response.json()
        return "SUCCESS" if result.get('success') else result.get('error')
    except Exception as e:
        return str(e)

# ==========================================
# 🌪️ MAIN APP
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

try:
    model = joblib.load(MODEL_FILE)
except Exception as e:
    st.error(f"Model Error: {e}")
    st.stop()

# ==========================================
# 📊 SIDEBAR
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
p1 = st.sidebar.text_input("Primary Contact", "+917678495189")
p2 = st.sidebar.text_input("Family Contact", "+918130631551")

# --- NEW: SIDEBAR READINESS CHECKLIST ---
st.sidebar.divider()
st.sidebar.subheader("✅ Readiness Checklist")
kit = st.sidebar.checkbox("Emergency Kit Ready")
charge = st.sidebar.checkbox("Phone/Powerbank Charged")
if kit and charge:
    st.sidebar.success("You are well prepared!")

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
        st.sidebar.warning("Please enter a valid number (e.g. +91...)")
    else:
        for t in targets:
            with st.sidebar.spinner(f"Sending to {t}..."):
                status = trigger_sos(t, loc_display, pres, current_status)
                if status == "SUCCESS": st.sidebar.success(f"✅ Sent to {t}")
                else: st.sidebar.error(f"Error {t}: {status}")

# ==========================================
# 🌍 2D DASHBOARD & MAP
# ==========================================
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Pressure", f"{pres} hPa")
    st.markdown(f"### Status: {current_status}")
    
    # Smart Warning based on prediction
    if prediction_idx >= 2:
        st.error("🚨 DANGER: Move to a safe location immediately!")
    elif prediction_idx == 1:
        st.warning("⚠️ ALERT: High winds expected. Be prepared.")

with col2:
    hex_colors = ["#00FF00", "#FFFF00", "#FFA500", "#FF0000"]
    active_color = hex_colors[prediction_idx]
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker([lat, lon], popup=loc_display).add_to(m)
    folium.Circle(location=[lat, lon], radius=15000, color=active_color, fill=True, fill_opacity=0.4).add_to(m)
    st_folium(m, width=700, height=450)

# ==========================================
# 📋 NEW: SURVIVAL GUIDE SECTION
# ==========================================
st.divider()
st.header("🩹 Cyclone Survival Guide")



tab1, tab2, tab3 = st.tabs(["🕒 Phase 1: Preparation", "🌪️ Phase 2: During Storm", "🏠 Phase 3: Recovery"])

with tab1:
    st.markdown("""
    **Before the cyclone hits:**
    * **🔋 Power:** Charge all phones and power banks to 100%.
    * **🎒 Go-Bag:** Keep a bag ready with water, snacks, dry food (biscuits), and a torch.
    * **🧹 Clean Up:** Move loose outdoor items (like trash bins or chairs) inside.
    * **🪟 Windows:** Close and lock all windows tightly.
    """)

with tab2:
    st.markdown("""
    **While the storm is active:**
    * **🚪 Stay Indoors:** Do not go out under any circumstances.
    * **🛡️ Safe Spot:** Stay in the strongest part of the house (hallway or small bathroom) away from glass windows.
    * **🔌 Electricity:** Switch off the main power supply and gas.
    * **⚠️ The Eye:** If the wind stops suddenly, **do not go out**. The wind will return from the other direction shortly.
    """)



with tab3:
    st.markdown("""
    **After the storm has passed:**
    * **📻 Listen:** Wait for official 'All Clear' news from the radio or authorities.
    * **⚡ Danger:** Stay away from fallen electric poles and broken wires.
    * **🏠 Inspection:** Check your house for cracks or damage before turning the power back on.
    """)