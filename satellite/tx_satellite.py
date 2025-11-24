import socket
import time
import json
import board
import busio
import adafruit_mlx90640

# --- CONFIGURATION ---
SATELLITE_PORT = 5000  # The "Channel" we transmit on

# --- HARDWARE SETUP ---
print("[SAT] Initializing Sensors...")
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

# --- COMMS SETUP ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 0.0.0.0 means "Listen on all network interfaces" (Wi-Fi, Ethernet, etc)
server_socket.bind(('0.0.0.0', SATELLITE_PORT))
server_socket.listen(1)

print(f"[SAT] Telemetry Downlink Active on Port {SATELLITE_PORT}")
print("[SAT] Waiting for Ground Station connection...")

# Buffer
frame = [0] * 768

while True:
    # Wait for Laptop to connect
    client_socket, addr = server_socket.accept()
    print(f"[SAT] Connected to Ground Station: {addr}")

    try:
        while True:
            # 1. Get Data
            mlx.getFrame(frame)
            
            # 2. Analyze High/Low for Telemetry
            max_temp = max(frame)
            status = "FIRE" if max_temp > 40 else "NOMINAL"

            # 3. Pack Data (JSON is easy to send)
            # We send a packet: { 'temp': [768 floats], 'status': 'NOMINAL' }
            packet = {
                "data": ["{:.2f}".format(x) for x in frame], # Format to 2 decimals to save bandwidth
                "status": status,
                "max": f"{max_temp:.1f}"
            }
            
            # 4. Transmit
            # We add a newline \n so the laptop knows where one packet ends
            data_string = json.dumps(packet) + "\n"
            client_socket.sendall(data_string.encode('utf-8'))
            
            # Throttle slightly to prevent network flood
            time.sleep(0.1)

    except (BrokenPipeError, ConnectionResetError):
        print("[SAT] Signal Lost. Scanning for Ground Station...")
        client_socket.close()
    except Exception as e:
        print(f"[SAT] Critical Error: {e}")
        break
