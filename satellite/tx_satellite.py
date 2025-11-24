import socket
import time
import struct
import board
import busio
import adafruit_mlx90640

# --- CONFIGURATION ---
SATELLITE_PORT = 5000 

# --- HARDWARE SETUP ---
print("[SAT] Initializing Sensors (RAW MODE)...")
try:
    i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
    mlx = adafruit_mlx90640.MLX90640(i2c)
    mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
except Exception as e:
    print(f"[SAT] ❌ Sensor Hardware Error: {e}")
    # Continue only for network testing if sensor fails
    mlx = None

# --- COMMS SETUP ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Allow immediate reuse of the port after restart
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('0.0.0.0', SATELLITE_PORT))
server_socket.listen(1)

print(f"[SAT] Raw Telemetry Downlink Active on Port {SATELLITE_PORT}")

# Pre-allocate buffer for 768 float values
frame = [0.0] * 768

while True:
    print("[SAT] Waiting for Ground Station...")
    client_socket, addr = server_socket.accept()
    print(f"[SAT] Connected: {addr}")

    try:
        while True:
            if mlx:
                # 1. Get Raw Data directly into memory
                try:
                    mlx.getFrame(frame)
                except RuntimeError:
                    # Sensor glitch, retry
                    continue
            else:
                # Mock data if sensor failed (for debugging)
                frame = [20.0] * 768

            # 2. Pack as Binary (Zero compute overhead)
            # '768f' = 768 float (4-byte) numbers packed together
            # This creates a 3072-byte binary blob
            binary_data = struct.pack('768f', *frame)

            # 3. Transmit Raw Bytes
            client_socket.sendall(binary_data)
            
            # Throttle slightly to match 4Hz refresh rate
            time.sleep(0.20)

    except (BrokenPipeError, ConnectionResetError):
        print("[SAT] Signal Lost. Resetting...")
        client_socket.close()
    except Exception as e:
        print(f"[SAT] Critical Error: {e}")
        client_socket.close()
        time.sleep(1)