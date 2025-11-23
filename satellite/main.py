import time
import board
import busio
import adafruit_mlx90640
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
# 40°C is good for testing with a hand or warm coffee.
# Real fire would be >100°C.
FIRE_THRESHOLD = 40.0 

# --- HARDWARE SETUP ---
print("Initializing Satellite Systems...")
# Setup I2C at 800kHz for faster video
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)

try:
    mlx = adafruit_mlx90640.MLX90640(i2c)
    print("Thermal Camera: ONLINE (Address 0x33)")
    mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
except Exception as e:
    print(f"Camera Init Failed: {e}")
    exit()

# --- VISUALIZATION SETUP ---
plt.ion() # Interactive mode ON
fig, ax = plt.subplots()
# Create a blank 24x32 grid
thermal_data = np.zeros((24, 32))
# 'inferno' is a good color map (Black=Cold, Yellow=Hot)
img = ax.imshow(thermal_data, cmap='inferno', vmin=20, vmax=40)
plt.colorbar(img)
plt.title("FLAMESAT Live Telemetry")

# Buffer for the 768 pixels
frame = [0] * 768

print("-" * 40)
print("MISSION START: Scanning for Heat Signatures...")

while True:
    try:
        # 1. Get Data from Camera
        mlx.getFrame(frame)
        
        # 2. Process Data
        data_array = np.array(frame).reshape((24, 32))
        max_temp = np.max(data_array)
        
        # 3. Update Heatmap
        img.set_data(data_array)
        # Adjust the color scale dynamically so you can see contrast
        img.set_clim(vmin=np.min(data_array), vmax=max_temp) 
        plt.pause(0.001) # Brief pause to let the window redraw

        # 4. FIRE LOGIC
        if max_temp > FIRE_THRESHOLD:
            print(f"⚠️ FIRE DETECTED! Max Temp: {max_temp:.1f}°C")
        else:
            # \r overwrites the line so your terminal stays clean
            print(f"Status: Nominal | Max Temp: {max_temp:.1f}°C", end='\r')

    except ValueError:
        continue # Sensor read error, skip frame
    except KeyboardInterrupt:
        print("\nMission Aborted by User.")
        break
