import socket
import json
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
# REPLACE THIS WITH YOUR PI'S IP ADDRESS
SATELLITE_IP = "10.54.254.151"
SATELLITE_PORT = 5000

# --- VISUAL SETUP ---
print("[GROUND] Initializing Mission Control Display...")
plt.ion()
fig, ax = plt.subplots(figsize=(8, 6))
thermal_data = np.zeros((24, 32))
img = ax.imshow(thermal_data, cmap='inferno', vmin=20, vmax=40)
plt.colorbar(img)
plt.title("Waiting for Signal...")

# --- COMMS SETUP ---
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    print(f"[GROUND] Dialing Satellite at {SATELLITE_IP}...")
    client_socket.connect((SATELLITE_IP, SATELLITE_PORT))
    print("[GROUND] Link Established! Receiving Telemetry...")
    
    # Create a file-like object to read lines easily
    socket_file = client_socket.makefile()

    while True:
        # 1. Listen for the next packet (ends with \n)
        line = socket_file.readline()
        if not line: break # Connection closed

        # 2. Decode JSON
        packet = json.loads(line)
        
        # 3. Reconstruct Image
        # Convert list of strings back to floats
        temp_list = [float(x) for x in packet['data']]
        data_array = np.array(temp_list).reshape((24, 32))
        
        # 4. Update Display
        img.set_data(data_array)
        img.set_clim(vmin=np.min(data_array), vmax=float(packet['max']))
        
        # Update Title with Telemetry
        status = packet['status']
        max_t = packet['max']
        
        if status == "FIRE":
            plt.title(f"⚠️ ALERT: FIRE DETECTED ({max_t}°C) ⚠️", color='red', fontweight='bold')
        else:
            plt.title(f"Status: {status} | Max Temp: {max_t}°C", color='black')
            
        plt.pause(0.001)

except ConnectionRefusedError:
    print("❌ Error: Satellite refused connection. Is the script running on the Pi?")
except KeyboardInterrupt:
    print("\n[GROUND] Mission Ended.")
    client_socket.close()
