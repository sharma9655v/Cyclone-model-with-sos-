import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score
import joblib
import warnings

warnings.filterwarnings('ignore')

print("="*80)
print("NORTH INDIAN OCEAN CYCLONE MODEL - RETRAINING WITH 'SAFE' DATA")
print("="*80)

# ============================================================================
# 1. LOAD IBTRACS DATA (STORM DATA)
# ============================================================================
print("\n[1] Loading Cyclone Data...")
file_path = 'ibtracs.NI.list.v04r01.csv'

try:
    df = pd.read_csv(
        file_path, header=None, usecols=[1, 8, 9, 10, 11], 
        names=['SEASON', 'LATITUDE', 'LONGITUDE', 'WIND_WMO', 'PRES_WMO'], 
        low_memory=False
    )
    
    # Cleanup
    for col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    df = df[df['SEASON'] >= 2000]
    
    # We keep everything >= 17 knots as "Storm Data"
    storm_df = df[df['WIND_WMO'] >= 17].copy()
    
    print(f"   Storm Records Found: {len(storm_df):,}")

except FileNotFoundError:
    print(f"\n❌ Error: '{file_path}' not found.")
    exit()

# ============================================================================
# 2. GENERATE SYNTHETIC "SAFE" DATA (CRITICAL STEP)
# ============================================================================
# The model needs to know what "Normal Weather" looks like to predict "Safe".
# We create 1000 random points representing calm ocean days.
print("\n[2] Generating 'Safe' Weather Patterns...")

safe_data = {
    'SEASON': np.random.randint(2000, 2024, 1000),
    'LATITUDE': np.random.uniform(5, 25, 1000),     # Random spots in ocean
    'LONGITUDE': np.random.uniform(60, 100, 1000),
    'WIND_WMO': np.random.uniform(5, 15, 1000),     # Low wind (5-15 kt)
    'PRES_WMO': np.random.uniform(1008, 1016, 1000) # High pressure (Normal)
}
safe_df = pd.DataFrame(safe_data)

# Combine Real Storms + Synthetic Safe Data
final_df = pd.concat([storm_df, safe_df], ignore_index=True)

# ============================================================================
# 3. DEFINE GRADES AND TRAIN
# ============================================================================
print("\n[3] Training Model...")

def cyclone_grade(wind):
    if wind < 17: return 0      # 🟢 SAFE
    elif wind <= 27: return 1   # 🟡 DEPRESSION
    elif wind <= 61: return 2   # 🟠 DEEP DEPRESSION/STORM
    else: return 3              # 🔴 SEVERE CYCLONE

final_df['GRADE'] = final_df['WIND_WMO'].apply(cyclone_grade)

X = final_df[['LATITUDE', 'LONGITUDE', 'PRES_WMO']].values
y = final_df['GRADE'].values

# Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
model = RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)
model.fit(X_train, y_train)

# Accuracy
y_pred = model.predict(X_test)
print(f"   Accuracy: {accuracy_score(y_test, y_pred)*100:.2f}%")

# Vizag Test Inside Training
print("\n[4] Sanity Check (Vizag Test):")
test_point = [[17.7, 83.3, 1012]] # Normal day
pred = model.predict(test_point)[0]
grade_map = {0:'SAFE', 1:'DEPRESSION', 2:'STORM', 3:'CYCLONE'}
print(f"   Input: 1012 mb -> Prediction: {grade_map[pred]} (Should be SAFE)")

# Save
joblib.dump(model, 'cyclone_model.joblib')
print("\n✅ Model Saved! Now run test_model.py")
import joblib
import numpy as np
import os

print("="*60)
print(" 🌪️  LIVE CYCLONE PREDICTOR (NORTH INDIAN OCEAN)")
print("="*60)

# 1. Load the saved model
# This file was created when you ran model.py
model_filename = 'cyclone_model.joblib'

if not os.path.exists(model_filename):
    print(f"❌ Error: '{model_filename}' not found!")
    print("   Please run 'model.py' once to train and save the model.")
    exit()

print("Loading model...", end="")
model = joblib.load(model_filename)
print(" Done! ✅")

# 2. Define the Grade Names
# These match the grades we defined during training
grade_names = {
    0: '🟢 SAFE / LOW PRESSURE (No Threat)',
    1: '🟡 DEPRESSION (Watch Required)',
    2: '🟠 DEEP DEPRESSION / CYCLONIC STORM (Warning)',
    3: '🔴 SEVERE CYCLONE (Danger!)'
}

# 3. Interactive Loop
while True:
    print("\n" + "-"*40)
    print("ENTER WEATHER DATA (or type 'exit' to quit)")
    
    user_input = input("Enter Latitude (e.g., 17.7): ")
    if user_input.lower() == 'exit': break
    
    try:
        lat = float(user_input)
        lon = float(input("Enter Longitude (e.g., 83.3): "))
        pres = float(input("Enter Pressure (mb/hPa, e.g., 1012): "))
        
        # Prepare input for the model
        features = [[lat, lon, pres]]
        
        # 1. Get the Class Prediction
        prediction_index = model.predict(features)[0]
        result = grade_names[prediction_index]
        
        # 2. Get the Confidence Score (Probability)
        all_probs = model.predict_proba(features)[0]
        # We grab the highest probability in the list to show confidence
        confidence = np.max(all_probs) * 100
        
        print(f"\n📢 PREDICTION: {result}")
        print(f"📊 CONFIDENCE: {confidence:.1f}%")

    except ValueError:
        print("❌ Invalid input! Please enter numbers only.")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\nStay Safe! 👋")