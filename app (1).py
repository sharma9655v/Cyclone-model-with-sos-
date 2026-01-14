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
# 🔑 CONFIGURATION
# ==========================================
WEATHER_API_KEY = "22223eb27d4a61523a6bbad9f42a14a7"

TWILIO_SID = "AC_YOUR_TWILIO_SID_HERE"
TWILIO_AUTH = "YOUR_TWILIO_AUTH_TOKEN_HERE"
TWILIO_PHONE = "+14176076960"

MODEL_FILE_NAME = "cyclone_model.joblib"
USERS_FILE = "users.csv"
# ==========================================

st.set_page_config(page_title="Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🔐 SESSION STATE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ==========================================
# 🔐 USER DATABASE
# ==========================================
if not os.path.exists(USERS_FILE):
    pd.DataFrame(
        columns=["Name", "Phone", "Email", "Password", "Created_At"]
    ).to_csv(USERS_FILE, index=False)

def signup(name, phone, email, password):
    df = pd.read_csv(USERS_FILE)
    if email in df["Email"].values:
        return False
    df.loc[len(df)] = [name, phone, email, password, datetime.now()]
    df.to_csv(USERS_FILE, index=False)
    return True

def login(email, password):
    df = pd.read_csv(USERS_FILE)
    return ((df["Email"] == email) & (df["Password"] == password)).any()

# ==========================================
# 🔐 LOGIN / SIGNUP UI
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 Cyclone Predictor – Login / Enrollment")

    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])

    with tab1:
        email = st.text_input("📧 Email")
        password = st.text_input("🔒 Password", type="password")
        if st.button("Login"):
            if login(email, password):
                st.session_state.logged_in = True
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid email or password")

    with tab2:
        name = st.text_input("👤 Full Name")
        phone = st.text_input("📱 Phone Number")
        email = st.text_input("📧 Email ID")
        password = st.text_input("🔒 Create Password", type="password")

        if st.button("Create Account"):
            if name and phone and email and password:
                if signup(name, phone, email, password):
                    st.success("Account created! Please login.")
                else:
                    st.error("Email already exists")
            else:
                st.warning("Please fill all fields")

    st.stop()

# ==========================================
# 🌪️ CYCLONE PREDICTOR (YOUR BASE CODE)
# ==========================================
st.title("🌪️ North Indian Ocean Cyclone Predictor")

if not os.path.exists(MODEL_FILE_NAME):
    st.error(f"❌ Model file not found: {MODEL_FILE_NAME}")
    st.stop()

model = joblib.load(MODEL_FILE_NAME)

# ==========================================
# 📊 SIDEBAR SETTINGS
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Select Mode:", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
enable_sms = st.sidebar.checkbox("Enable SMS Alerts", value=True)
phone_1 = st.sidebar.text_input("Contact 1 (Primary):", "+919999999999")
phone_2 = st.sidebar.text_input("Contact 2 (Family):", "")
phone_3 = st.sidebar.text_input("Contact 3 (Authorities):", "")

# ==========================================
# 🆘 SOS FUNCTION
# ==========================================
def send_sms_alert(phone, location, pressure):
    try:
        if "YOUR_TWILIO" in TWILIO_SID:
            return "SIMULATION"
        client = Client(TWILIO_SID, TWILIO_AUTH)
        client.messages.create(
            body=f"""🚨 CYCLONE SOS ALERT 🚨
Location: {location}
Pressure: {pressure} hPa
Immediate help required.""",
            from_=TWILIO_PHONE,
            to=phone
        )
        return "SENT"
    except Exception as e:
        return f"ERROR: {e}"

# ==========================================
# 🆘 SOS BUTTON
# ==========================================
st.sidebar.divider()
st.sidebar.header("🆘 Emergency Panic Button")

if st.sidebar.button("🚨 TRIGGER SOS NOW", use_container_width=True):
    phone_list = [p for p in [phone_1, phone_2, phone_3] if p and len(p) > 5]
    if not phone_list:
        st.sidebar.warning("No emergency contacts entered")
    else:
        with st.sidebar.spinner("Sending SOS alerts..."):
            for phone in phone_list:
                status = send_sms_alert(
                    phone,
                    st.session_state.get("loc_name", "Unknown"),
                    st.session_state.get("cur_pres", "Unknown")
                )
                if status == "SENT":
                    st.sidebar.success(f"✅ SOS sent to {phone}")
                elif status == "SIMULATION":
                    st.sidebar.info(f"📲 [Simulation] SOS triggered for {phone}")
                else:
                    st.sidebar.error(status)

# ==========================================
# 🌍 WEATHER DATA
# ==========================================
lat, lon, pres = 17.7, 83.3, 1012.0
location_name = "Vizag (Default)"

if mode == "📡 Live Weather (API)":
    city = st.sidebar.text_input("Enter City Name:", "Visakhapatnam")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]
        pres = data["main"]["pressure"]
        location_name = f"{data['name']}, {data['sys']['country']}"
        st.sidebar.success("Live data fetched")

else:
    location_name = "Custom Simulation"
    lat = st.sidebar.slider("Latitude", 0.0, 30.0, lat)
    lon = st.sidebar.slider("Longitude", 50.0, 100.0, lon)
    pres = st.sidebar.slider("Pressure (hPa)", 900, 1020, pres)

st.session_state["loc_name"] = location_name
st.session_state["cur_pres"] = pres

# ==========================================
# 🔮 PREDICTION
# ==========================================
features = [[lat, lon, pres]]
prediction_index = model.predict(features)[0]
confidence = np.max(model.predict_proba(features)[0]) * 100

grades = {
    0: "🟢 SAFE",
    1: "🟡 DEPRESSION",
    2: "🟠 STORM",
    3: "🔴 CYCLONE"
}

# ==========================================
# 📊 DASHBOARD
# ==========================================
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader(f"📍 {location_name}")
    st.metric("Pressure", f"{pres} hPa")
    if prediction_index >= 2:
        st.error(f"## {grades[prediction_index]}")
    else:
        st.success(f"## {grades[prediction_index]}")
    st.write(f"**Confidence:** {confidence:.1f}%")

with col2:
    st.subheader("🛰️ Live Risk Map")
    m = folium.Map(location=[lat, lon], zoom_start=11)
    folium.Marker([lat, lon], popup=location_name).add_to(m)
    st_folium(m, width=800, height=500)
