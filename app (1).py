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
# 🔑 SECURE CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_AUTH = st.secrets["TWILIO_AUTH"]
    TWILIO_PHONE = st.secrets["TWILIO_PHONE"]
except Exception:
    st.error("❌ Twilio Secrets missing! Add TWILIO_SID, TWILIO_AUTH, and TWILIO_PHONE to Streamlit Secrets.")
    st.stop()

MODEL_FILE_NAME = 'cyclone_model.joblib'

# ==========================================
# 🆘 SOS & LOCATION LOGIC
# ==========================================
def get_ip_location():
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        data = response.json()
        return data.get("latitude"), data.get("longitude"), "Approximate (IP)"
    except:
        return None, None, None

def trigger_emergency_system(lat, lon, loc_type, phone1, phone2):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    map_url = f"https://www.google.com/maps?q={lat},{lon}"
    contacts = [p for p in [phone1, phone2] if p]
    
    for p in contacts:
        try:
            # 1. SMS Alert
            client.messages.create(
                body=f"🚨 SOS! Cyclone Project Alert. User Location ({loc_type}): {map_url}",
                from_=TWILIO_PHONE, to=p
            )
            # 2. Hindi Voice Call
            client.calls.create(
                twiml=f'<Response><Say language="hi-IN">Emergency alert! Cyclone khatra hai. Location aapko SMS kar di gayi hai.</Say></Response>',
                from_=TWILIO_PHONE, to=p
            )
            st.toast(f"✅ Alert sent to {p}")
        except Exception as e:
            st.error(f"Failed to alert {p}: {e}")

# ==========================================
# 🌪️ MAIN APP UI
# ==========================================
st.set_page_config(page_title="Cyclone 3D SOS", layout="wide", initial_sidebar_state="expanded")
st.title("🌪️ Cyclone Predictor & 3D Emergency Hub")

# SIDEBAR SOS SECTION
st.sidebar.header("🆘 Emergency SOS")
location_data = streamlit_geolocation()
phone_1 = st.sidebar.text_input("Primary Contact:", "+919999999999")
phone_2 = st.sidebar.text_input("Secondary Contact:", "")

if st.sidebar.button("🚨 TRIGGER SOS NOW", type="primary", use_container_width=True):
    lat = location_data.get('latitude')
    lon = location_data.get('longitude')
    l_type = "Precise (GPS)"
    
    if lat is None:
        lat, lon, l_type = get_ip_location()
        
    if lat:
        trigger_emergency_system(lat, lon, l_type, phone_1, phone_2)
        st.sidebar.success(f"SOS Sent! ({l_type})")
    else:
        st.sidebar.error("Could not find location. Enable GPS.")

# PREDICTION DATA
st.sidebar.divider()
city = st.sidebar.text_input("Analyze City:", "Visakhapatnam")
res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}")

if res.status_code == 200:
    data = res.json()
    c_lat, c_lon, pres = data['coord']['lat'], data['coord']['lon'], data['main']['pressure']
    
    # AI Prediction
    model = joblib.load(MODEL_FILE_NAME)
    prediction = model.predict([[c_lat, c_lon, pres]])[0]
    
    # 3D MAP SECTION
    st.subheader(f"3D Risk Visualization: {city}")
    
    # Create data for 3D plot
    chart_data = pd.DataFrame({
        'lat': [c_lat],
        'lon': [c_lon],
        'pressure': [pres],
        'risk': [prediction * 100] # Height based on risk level
    })

    

    # Pydeck 3D Map Logic
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/dark-v9',
        initial_view_state=pdk.ViewState(
            latitude=c_lat,
            longitude=c_lon,
            zoom=10,
            pitch=50, # Tilts the map for 3D effect
        ),
        layers=[
            # 3D Column representing the storm intensity
            pdk.Layer(
                'ColumnLayer',
                data=chart_data,
                get_position='[lon, lat]',
                get_elevation='risk',
                elevation_scale=100,
                radius=1000,
                get_fill_color=[255, 0, 0, 150] if prediction >= 2 else [0, 255, 0, 150],
                pickable=True,
                auto_highlight=True,
            ),
        ],
        tooltip={"text": "Pressure: {pressure} hPa\nRisk Level: {risk}"}
    ))

    # STATUS METRICS
    m1, m2, m3 = st.columns(3)
    m1.metric("Atmospheric Pressure", f"{pres} hPa")
    m2.metric("Latitude/Longitude", f"{c_lat}, {c_lon}")
    m3.metric("Risk Status", "🔴 DANGER" if prediction >= 2 else "🟢 SAFE")
else:
    st.warning("Please enter a valid city name to see the 3D map.")