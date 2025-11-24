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
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

# --- COMMS SETUP ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('0.0.0.0', SATELLITE_PORT))
server_socket.listen(1)

print(f"[SAT] Raw Telemetry Downlink Active on Port {SATELLITE_PORT}")

# Pre-allocate buffer
frame = [0] * 768
# 768 floats * 4 bytes each = 3072 bytes per frame
PACKET_SIZE = 768 * 4 

while True:
    client_socket, addr = server_socket.accept()
    print(f"[SAT] Connected: {addr}")

    try:
        while True:
            # 1. Get Raw Data
            mlx.getFrame(frame)
            
            # 2. Pack as Binary (Zero compute overhead)
            # '768f' means 768 floats packed consecutively
            binary_data = struct.pack('768f', *frame)

            # 3. Transmit Raw Bytes
            client_socket.sendall(binary_data)
            
            # minimal throttle
            time.sleep(0.1)

    except (BrokenPipeError, ConnectionResetError):
        print("[SAT] Signal Lost. Resetting...")
        client_socket.close()
    except Exception as e:
        print(f"[SAT] Error: {e}")
        break