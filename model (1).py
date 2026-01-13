import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score
import joblib
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

print("="*80)
print("NORTH INDIAN OCEAN CYCLONE MODEL - IBTRACS NI LIST TRAINING")
print("="*80)

# ============================================================================
# STEP 1: LOAD IBTRACS DATA
# ============================================================================
print("\n[STEP 1] Loading IBTrACS NI Data...")

file_path = 'ibtracs.NI.list.v04r01.csv'

try:
    # Use header=None to handle files starting with data
    # Columns: 1=SEASON, 8=LAT, 9=LON, 10=WIND, 11=PRES
    df = pd.read_csv(
        file_path, 
        header=None,  
        usecols=[1, 8, 9, 10, 11], 
        names=['SEASON', 'LATITUDE', 'LONGITUDE', 'WIND_WMO', 'PRES_WMO'], 
        low_memory=False
    )
    
    print("   Data Loaded Successfully!")

except FileNotFoundError:
    print(f"\nCRITICAL ERROR: File '{file_path}' not found.")
    exit()

# Clean data types
cols_to_clean = ['SEASON', 'LATITUDE', 'LONGITUDE', 'WIND_WMO', 'PRES_WMO']
for col in cols_to_clean:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Drop missing and filter
df = df.dropna()
df = df[df['SEASON'] >= 2000]
df = df[df['WIND_WMO'].between(17, 200)]

print(f"   Records: {len(df):,}")

# ============================================================================
# STEP 2: CREATE GRADES
# ============================================================================
print("\n[STEP 2] Feature Engineering...")

def cyclone_grade(wind):
    if wind < 17: return 0      
    elif wind <= 27: return 1   
    elif wind <= 61: return 2   
    else: return 3              

df['GRADE'] = df['WIND_WMO'].apply(cyclone_grade)

features = ['LATITUDE', 'LONGITUDE', 'PRES_WMO']
X = df[features].values
y = df['GRADE'].values

# ============================================================================
# STEP 3: TRAIN MODEL
# ============================================================================
print("\n[STEP 3] Training Random Forest...")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

param_grid = {
    'n_estimators': [100],
    'max_depth': [10],
    'min_samples_split': [5]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42, n_jobs=-1),
    param_grid, cv=3, scoring='accuracy'
)

model = grid_search.fit(X_train, y_train)
best_model = model.best_estimator_

# ============================================================================
# STEP 4: EVALUATION & TESTS
# ============================================================================
y_pred = best_model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"   Accuracy: {acc*100:.2f}%")

# FIXED LINE BELOW
print("\n[STEP 4] Testing Specific Locations (Vizag: 17.7N, 83.3E)...")

vizag_tests = [
    [17.7, 83.3, 1012], 
    [17.7, 83.3, 1000], 
    [17.7, 83.3, 980],  
    [17.7, 83.3, 950]   
]

grade_names = {
    0: 'SAFE / LOW PRESSURE', 
    1: 'DEPRESSION', 
    2: 'DEEP DEPRESSION/STORM', 
    3: 'SEVERE CYCLONE'
}

for test in vizag_tests:
    pred = best_model.predict([test])[0]
    print(f"   Lat:{test[0]} Pres:{test[2]} -> {grade_names[pred]}")

# ============================================================================
# STEP 5: SAVE
# ============================================================================
print("\n[STEP 5] Saving Model...")
joblib.dump(best_model, 'cyclone_model.joblib')
print("   Saved cyclone_model.joblib")
print("   DONE!")