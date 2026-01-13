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
# 🔑 CONFIGURATION (Using Secrets)
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

# Fetching credentials from Streamlit Secrets vault
try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
except:
    st.error("❌ Twilio Secrets not found! Add them in Settings > Secrets.")
    st.stop()

CSV_FILE_NAME = 'ibtracs.NI.list.v04r01.zip' 
MODEL_FILE_NAME = 'cyclone_model.joblib'

# ==========================================
# 🆘 EMERGENCY SOS LOGIC
# ==========================================
def trigger_sos_alerts(phones, lat, lon):
    """Sends SMS and Hindi Voice Call via Twilio"""
    client = Client(TWILIO_SID, TWILIO_AUTH)
    map_url = f"https://www.google.com/maps?q={lat},{lon}"
    
    for p in phones:
        if p and len(p) > 5:
            try:
                # 1. Send SMS Alert
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

# 1. PAGE SETUP
st.set_page_config(page_title="Cyclone 3D SOS", layout="wide")
st.title("🌪️ North Indian Ocean Cyclone Predictor & 3D SOS Hub")

# 2. LOAD AI MODEL
model = joblib.load(MODEL_FILE_NAME)

# 3. SIDEBAR: EMERGENCY HUB
st.sidebar.header("🚨 Emergency Hub")
location_data = streamlit_geolocation() # Captures GPS from browser
phone_1 = st.sidebar.text_input("Primary Contact:", "+919999999999")
phone_2 = st.sidebar.text_input("Secondary Contact:", "")

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    if location_data['latitude']:
        trigger_sos_alerts([phone_1, phone_2], location_data['latitude'], location_data['longitude'])
        st.sidebar.success("🆘 SOS Signals Sent!")
    else:
        st.sidebar.warning("📍 Please allow location access in your browser.")

# 4. WEATHER DATA FETCHING
st.sidebar.divider()
city = st.sidebar.text_input("Analyze City Risk:", "Visakhapatnam")
weather_res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}").json()

if 'coord' in weather_res:
    cur_lat, cur_lon = weather_res['coord']['lat'], weather_res['coord']['lon']
    cur_pres = weather_res['main']['pressure']
    
    # 5. AI PREDICTION
    prediction = model.predict([[cur_lat, cur_lon, cur_pres]])[0]
    risk_height = (prediction + 1) * 2000 # Elevation for 3D bar
    
    # 6. 3D MAP VISUALIZATION
    st.subheader(f"🛰️ 3D Storm Intensity Map: {city}")
    
    # Prepare data for 3D Column
    map_df = pd.DataFrame({'lat': [cur_lat], 'lon': [cur_lon], 'elevation': [risk_height]})

    

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/navigation-night-v1',
        initial_view_state=pdk.ViewState(
            latitude=cur_lat,
            longitude=cur_lon,
            zoom=10,
            pitch=50, # Tilts the map for 3D perspective
        ),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=map_df,
                get_position='[lon, lat]',
                get_elevation='elevation',
                elevation_scale=1,
                radius=2000,
                get_fill_color=[255, 0, 0, 160] if prediction >= 2 else [0, 255, 0, 160],
                pickable=True,
                extruded=True,
            ),
        ],
    ))
    
    # Status Metrics
    m1, m2 = st.columns(2)
    m1.metric("Atmospheric Pressure", f"{cur_pres} hPa")
    m2.metric("Risk Status", "🔴 DANGER" if prediction >= 2 else "🟢 SAFE")