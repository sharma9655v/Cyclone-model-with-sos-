import streamlit as st
import joblib
import numpy as np
import pandas as pd
import requests
import os
import pydeck as pdk
from twilio.rest import Client
from streamlit_geolocation import streamlit_geolocation

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Use Streamlit Secrets for these values in production
try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
except:
    # Fallback for local testing (Replace with your actual keys)
    TWILIO_SID = "AC_YOUR_TWILIO_SID_HERE"
    TWILIO_AUTH = "YOUR_TWILIO_AUTH_TOKEN_HERE"
    TWILIO_PHONE = "+1234567890"

MODEL_FILE_NAME = 'cyclone_model.joblib'
# ==========================================

# 1. PAGE CONFIG
st.set_page_config(page_title="Cyclone 3D SOS", page_icon="🌪️", layout="wide")
st.title("🌪️ Cyclone Predictor & 3D SOS Hub")

# 2. LOAD MODEL
if not os.path.exists(MODEL_FILE_NAME):
    st.error(f"❌ Model file '{MODEL_FILE_NAME}' not found.")
    st.stop()
model = joblib.load(MODEL_FILE_NAME)

# 3. SIDEBAR: EMERGENCY CONTACTS & SOS
st.sidebar.header("🚨 Emergency Hub")
phone_1 = st.sidebar.text_input("Primary Contact:", "+919999999999")
phone_2 = st.sidebar.text_input("Secondary Contact:", "")

# Geolocation component
location_data = streamlit_geolocation()

def trigger_sos_alerts(phones, lat, lon):
    """Sends SMS and Hindi Voice Call via Twilio"""
    client = Client(TWILIO_SID, TWILIO_AUTH)
    map_url = f"https://www.google.com/maps?q={lat},{lon}"
    
    for p in phones:
        if p and len(p) > 5:
            try:
                # 1. SMS Alert
                client.messages.create(
                    body=f"🚨 SOS CYCLONE ALERT! User needs help. Location: {map_url}",
                    from_=TWILIO_PHONE,
                    to=p
                )
                # 2. Hindi Voice Call
                client.calls.create(
                    twiml=f'''
                    <Response>
                        <Say language="hi-IN">Emergency alert! Cyclone khatra hai. Location SMS kar di gayi hai. Kripya turant sahayata bheje.</Say>
                    </Response>
                    ''',
                    from_=TWILIO_PHONE,
                    to=p
                )
                st.toast(f"✅ Alert sent to {p}")
            except Exception as e:
                st.sidebar.error(f"Error alerting {p}: {e}")

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    if location_data['latitude']:
        trigger_sos_alerts([phone_1, phone_2], location_data['latitude'], location_data['longitude'])
        st.sidebar.success("🆘 SOS Signals Sent!")
    else:
        st.sidebar.warning("📍 Please allow location access in your browser.")

# 4. WEATHER DATA FETCHING
st.sidebar.divider()
city = st.sidebar.text_input("Check City Risk:", "Visakhapatnam")
weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
res = requests.get(weather_url).json()

if 'coord' in res:
    cur_lat, cur_lon = res['coord']['lat'], res['coord']['lon']
    cur_pres = res['main']['pressure']
    
    # 5. PREDICTION
    prediction = model.predict([[cur_lat, cur_lon, cur_pres]])[0]
    risk_level = (prediction + 1) * 25  # Scale for 3D height
    
    # 6. DASHBOARD & 3D MAP
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader(f"📍 {city}")
        st.metric("Pressure", f"{cur_pres} hPa")
        if prediction >= 2:
            st.error("🔴 HIGH RISK / DANGER")
        elif prediction == 1:
            st.warning("🟡 MODERATE RISK")
        else:
            st.success("🟢 LOW RISK / SAFE")

    with col2:
        st.subheader("🛰️ 3D Storm Intensity Map")
        
        # Prepare 3D Data
        map_df = pd.DataFrame({
            'lat': [cur_lat],
            'lon': [cur_lon],
            'elevation': [risk_level * 100]
        })

        

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/navigation-night-v1',
            initial_view_state=pdk.ViewState(
                latitude=cur_lat,
                longitude=cur_lon,
                zoom=10,
                pitch=50, # 3D Tilt
            ),
            layers=[
                pdk.Layer(
                    'ColumnLayer',
                    data=map_df,
                    get_position='[lon, lat]',
                    get_elevation='elevation',
                    elevation_scale=100,
                    radius=1500,
                    get_fill_color=[255, 0, 0, 150] if prediction >= 2 else [0, 255, 0, 150],
                    pickable=True,
                    extruded=True,
                ),
            ],
        ))
else:
    st.info("Enter a city name to generate the 3D map.")