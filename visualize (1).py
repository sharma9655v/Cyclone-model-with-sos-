import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

print("="*60)
print(" 🗺️  GENERATING CYCLONE HEATMAP (NORTH INDIAN OCEAN)")
print("="*60)

# 1. LOAD DATA
file_path = 'ibtracs.NI.list.v04r01.csv'
print("Loading data...", end="")

try:
    # We load the data using the same logic as the model
    df = pd.read_csv(
        file_path, 
        header=None, 
        usecols=[1, 8, 9, 10], 
        names=['SEASON', 'LATITUDE', 'LONGITUDE', 'WIND'], 
        low_memory=False
    )
    
    # Clean up
    df = df.apply(pd.to_numeric, errors='coerce').dropna()
    df = df[df['SEASON'] >= 2000]
    df = df[df['WIND'] >= 17] # Only show actual storms
    
    print(f" Done! ({len(df)} storm points found)")

except FileNotFoundError:
    print("\n❌ Error: CSV file not found.")
    exit()

# 2. SETUP THE MAP
plt.figure(figsize=(14, 8))
plt.title('North Indian Ocean Cyclone Tracks (2000-Present)', fontsize=16, fontweight='bold')

# 3. DRAW THE OCEAN
# We load a background map image
try:
    img = plt.imread("https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/World_map_blank_without_borders.svg/2000px-World_map_blank_without_borders.svg.png")
    plt.imshow(img, extent=[-180, 180, -90, 90], alpha=0.2)
except:
    print("⚠️ Warning: Could not load internet map. Plotting white background.")

# 4. PLOT THE CYCLONES
# Color matches Wind Speed (Blue=Weak -> Red=Strong)
scatter = plt.scatter(
    df['LONGITUDE'], 
    df['LATITUDE'], 
    c=df['WIND'], 
    cmap='jet', 
    s=df['WIND']/1.5, # Size matches storm size
    alpha=0.6,
    edgecolors='none'
)

# 5. MARK VIZAG
plt.plot(83.3, 17.7, 'k*', markersize=15, label='Vizag')
plt.text(83.5, 17.5, 'Vizag', fontsize=12, fontweight='bold')

# 6. FOCUS ON INDIA
plt.xlim(50, 100)
plt.ylim(0, 30)
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.colorbar(scatter, label='Wind Speed (knots)')
plt.grid(True, linestyle='--', alpha=0.3)
plt.legend()

print("\n📊 Map generated! Look at the popup window.")
print("   (Close the window to finish the script)")
plt.show()