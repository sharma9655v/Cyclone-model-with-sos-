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
# 🔑 CONFIGURATION (Using Secrets)
# ==========================================
try:
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
    # Account 1
    TWILIO_SID_1 = st.secrets["TWILIO_SID_1"]
    TWILIO_AUTH_1 = st.secrets["TWILIO_AUTH_1"]
    TWILIO_PHONE_1 = st.secrets["TWILIO_PHONE_1"]
    # Account 2
    TWILIO_SID_2 = st.secrets["TWILIO_SID_2"]
    TWILIO_AUTH_2 = st.secrets["TWILIO_AUTH_2"]
    TWILIO_PHONE_2 = st.secrets["TWILIO_PHONE_2"]
    SIMULATION_MODE = False
except Exception:
    # Fallback to simulation if secrets are missing
    SIMULATION_MODE = True

MODEL_FILE = "cyclone_model.joblib"
USERS_FILE = "users.csv"

st.set_page_config(page_title="3D Cyclone Predictor", page_icon="🌪️", layout="wide")

# ==========================================
# 🔐 SESSION INITIALIZATION
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "loc_name" not in st.session_state:
    st.session_state.loc_name = "Visakhapatnam"
if "cur_pres" not in st.session_state:
    st.session_state.cur_pres = 1012

# ==========================================
# 🔐 USER AUTH FUNCTIONS
# ==========================================
if not os.path.exists(USERS_FILE):
    pd.DataFrame(columns=["Name", "Phone", "Email", "Password", "Created"]).to_csv(USERS_FILE, index=False)

def login(email, password):
    df = pd.read_csv(USERS_FILE)
    # Ensure password is treated as string for comparison
    user_match = df[(df["Email"] == email) & (df["Password"].astype(str) == str(password))]
    return not user_match.empty

def signup(name, phone, email, password):
    df = pd.read_csv(USERS_FILE)
    if email in df["Email"].values: return False
    new_user = pd.DataFrame([[name, phone, email, str(password), datetime.now()]], 
                            columns=["Name", "Phone", "Email", "Password", "Created"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USERS_FILE, index=False)
    return True

# ==========================================
# 🆘 SOS FUNCTION (DUAL ACCOUNT FAILOVER)
# ==========================================
def trigger_sos(target_phone, location, pressure, label):
    if SIMULATION_MODE: return "SIMULATION"
    
    accounts = [
        {"sid": TWILIO_SID_1, "token": TWILIO_AUTH_1, "from": TWILIO_PHONE_1},
        {"sid": TWILIO_SID_2, "token": TWILIO_AUTH_2, "from": TWILIO_PHONE_2}
    ]
    
    last_err = ""
    for acc in accounts:
        try:
            client = Client(acc["sid"], acc["token"])
            # SMS (English)
            client.messages.create(
                body=f"🚨 SOS: Cyclone Risk!\nStatus: {label}\nLocation: {location}\nPressure: {pressure} hPa",
                from_=acc["from"], to=target_phone
            )
            # Voice (Hindi)
            call_twiml = f'<Response><Say language="hi-IN">Saavdhan! {location} mein chakravaat ka khatra hai.</Say></Response>'
            client.calls.create(twiml=call_twiml, to=target_phone, from_=acc["from"])
            return "SUCCESS"
        except Exception as e:
            last_err = str(e)
            continue
    return last_err

# ==========================================
# 🔐 LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 Cyclone Predictor Login")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        le = st.text_input("Email", key="l_email")
        lp = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            if login(le, lp):
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Invalid credentials")
    with t2:
        sn = st.text_input("Full Name", key="s_name")
        sp = st.text_input("Phone Number", key="s_phone")
        se = st.text_input("Email ID", key="s_email")
        spa = st.text_input("Create Password", type="password", key="s_pass")
        if st.button("Sign Up"):
            if sn and sp and se and spa:
                if signup(sn, sp, se, spa): st.success("Account created! Log in now.")
                else: st.error("Email already exists.")
            else: st.warning("Please fill all fields.")
    st.stop()

# ==========================================
# 🌪️ MAIN APP & SIDEBAR
# ==========================================
st.sidebar.header("Data Source")
mode = st.sidebar.radio("Input Mode", ["📡 Live Weather (API)", "🎛️ Manual Simulation"])

st.sidebar.divider()
st.sidebar.header("🚨 Emergency Contacts")
p1 = st.sidebar.text_input("Primary Contact", "+919999999999")
p2 = st.sidebar.text_input("Family Contact", "")

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

st.session_state.loc_name, st.session_state.cur_pres = loc_display, pres

# --- PREDICTION ---
try:
    model = joblib.load(MODEL_FILE)
    labels = ["🟢 SAFE", "🟡 DEPRESSION", "🟠 STORM", "🔴 CYCLONE"]
    prediction_idx = model.predict(np.array([[lat, lon, pres]]))[0]
    current_status = labels[prediction_idx]
except Exception as e:
    st.error(f"Model Error: {e}")
    st.stop()

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
                elif status == "SIMULATION": st.sidebar.info(f"Simulated SOS to {t}")
                else: st.sidebar.error(f"Error: {status}")

# ==========================================
# 🌍 3D DASHBOARD & PYDECK MAP
# ==========================================
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader(f"📍 {loc_display}")
    st.metric("Pressure", f"{pres} hPa")
    st.markdown(f"### Status: {current_status}")
    if prediction_idx >= 2: st.warning("⚠️ CRITICAL RISK DETECTED!")

with c2:
    # 3D Coloring Logic
    colors = [[0, 255, 0, 150], [255, 255, 0, 150], [255, 165, 0, 150], [255, 0, 0, 180]]
    active_color = colors[prediction_idx]

    # Layers for 3D Map
    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=9, pitch=45)
    
    # Layer 1: Highlighted circular boundary
    boundary_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": lat, "lon": lon}]),
        get_position="[lon, lat]",
        get_color=active_color,
        get_radius=15000, 
    )
    
    # Layer 2: 3D Pillar
    pillar_layer = pdk.Layer(
        "ColumnLayer",
        data=pd.DataFrame([{"lat": lat, "lon": lon, "h": float((4 - prediction_idx) * 3000), "status": current_status}]),
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
        tooltip={"text": "Current Status: {status}"}
    ))