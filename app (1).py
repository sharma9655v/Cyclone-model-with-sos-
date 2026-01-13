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
# 🔑 CONFIGURATION & SECRETS
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
except:
    st.error("❌ Twilio Secrets missing in Dashboard!")
    st.stop()

MODEL_FILE_NAME = 'cyclone_model.joblib'

# ==========================================
# 🆘 SOS SYSTEM LOGIC
# ==========================================
def trigger_sos(phone, lat, lon):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        map_url = f"http://google.com/maps?q={lat},{lon}"
        # SMS Alert
        client.messages.create(
            body=f"🚨 SOS CYCLONE! User location: {map_url}",
            from_=TWILIO_PHONE, to=phone
        )
        # Hindi Voice Call
        client.calls.create(
            twiml=f'<Response><Say language="hi-IN">Emergency alert! Cyclone khatra hai. Location SMS kar di gayi hai.</Say></Response>',
            from_=TWILIO_PHONE, to=phone
        )
        return True
    except: return False

# 1. PAGE SETUP
st.set_page_config(page_title="Cyclone 3D SOS", layout="wide")
st.title("🌪️ Cyclone Predictor & 3D Emergency Map")

# 2. SIDEBAR SOS
st.sidebar.header("🆘 Emergency SOS")
loc = streamlit_geolocation()
p1 = st.sidebar.text_input("Contact 1:", "+919999999999")

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary"):
    if loc['latitude']:
        if trigger_sos(p1, loc['latitude'], loc['longitude']):
            st.sidebar.success("✅ SOS and Hindi Call Sent!")
    else:
        st.sidebar.warning("📍 Please allow GPS access.")

# 3. WEATHER & PREDICTION
city = st.sidebar.text_input("Enter City:", "Visakhapatnam")
res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}").json()

if 'coord' in res:
    lat, lon, pres = res['coord']['lat'], res['coord']['lon'], res['main']['pressure']
    model = joblib.load(MODEL_FILE_NAME)
    prediction = model.predict([[lat, lon, pres]])[0]

    # --- 🗺️ 3D MAP VISUALIZATION ---
    st.subheader(f"3D Risk Map: {city}")
    
    # Create data for 3D bars
    map_data = pd.DataFrame({'lat': [lat], 'lon': [lon], 'risk': [prediction * 100 + 10]})

    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/navigation-night-v1',
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=11,
            pitch=50, # This creates the 3D tilt
        ),
        layers=[
            pdk.Layer(
                'ColumnLayer',
                data=map_data,
                get_position='[lon, lat]',
                get_elevation='risk',
                elevation_scale=100,
                radius=1000,
                get_fill_color=[255, 0, 0, 150] if prediction >= 2 else [0, 255, 0, 150],
                pickable=True,
                extruded=True,
            ),
        ],
    ))
    
    st.metric("Risk Level", "🔴 DANGER" if prediction >= 2 else "🟢 SAFE")