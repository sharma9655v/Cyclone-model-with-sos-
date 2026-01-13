import joblib
import numpy as np
import os

print("="*60)
print(" 🌪️  LIVE CYCLONE PREDICTOR (NORTH INDIAN OCEAN)")
print("="*60)

# 1. Load the saved model
model_filename = 'cyclone_model.joblib'

if not os.path.exists(model_filename):
    print(f"❌ Error: '{model_filename}' not found!")
    print("   Run model.py first to train and save the model.")
    exit()

print("Loading model...", end="")
model = joblib.load(model_filename)
print(" Done! ✅")

# 2. Define the Grade Names (Must match your training script)
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
        pres = float(input("Enter Pressure (mb/hPa, e.g., 1000): "))
        
        # 4. Predict
        # input must be 2D array: [[lat, lon, pres]]
        features = [[lat, lon, pres]]
        prediction_index = model.predict(features)[0]
        result = grade_names[prediction_index]
        
        # Get confidence (probability)
        probs = model.predict_proba(features)[0]
        confidence = probs[prediction_index] * 100
        
        print(f"\n📢 PREDICTION: {result}")
        print(f"📊 CONFIDENCE: {confidence:.1f}%")
        
        # Simple Logic check
        if pres < 980 and prediction_index < 2:
            print("⚠️ NOTE: Pressure is very low. Model might be underestimating.")

    except ValueError:
        print("❌ Invalid input! Please enter numbers only.")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\nStay Safe! 👋")