import socket
import time
import struct
import board
import busio
import adafruit_mlx90640
import threading
import subprocess
import os
import json

# --- CONFIGURATION ---
TELEM_PORT = 5000
CMD_PORT = 5001
SECRETS_FILE = "secrets.json"

# Load Secret Password
COMMAND_PASSWORD = None
try:
    with open(SECRETS_FILE) as f:
        secrets = json.load(f)
        COMMAND_PASSWORD = secrets.get("command_password")
except Exception:
    print("[SAT] ⚠️  WARNING: secrets.json not found or invalid.")

if not COMMAND_PASSWORD:
    print("[SAT] ❌ NO PASSWORD SET. COMMAND LINK DISABLED FOR SECURITY.")

def init_sensor():
    print("[SAT] Initializing Sensors...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
        mlx = adafruit_mlx90640.MLX90640(i2c)
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
        return mlx
    except Exception as e:
        print(f"[SAT] ❌ Sensor Error: {e}")
        return None

def command_listener():
    if not COMMAND_PASSWORD:
        return

    cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cmd_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    cmd_socket.bind(('0.0.0.0', CMD_PORT))
    cmd_socket.listen(1)
    print(f"[SAT] Secure Command Uplink Active on Port {CMD_PORT}")

    while True:
        try:
            conn, addr = cmd_socket.accept()
            # Receive packet
            raw_data = conn.recv(4096).strip().decode('utf-8')
            
            # AUTHENTICATION CHECK
            # Format must be: "PASSWORD|COMMAND"
            if "|" in raw_data:
                password, command_str = raw_data.split("|", 1)
                
                if password == COMMAND_PASSWORD:
                    # --- AUTH SUCCESS ---
                    print(f"[SAT] ⚠️ Executing: {command_str}")
                    try:
                        result = subprocess.run(
                            command_str, 
                            shell=True, 
                            capture_output=True, 
                            text=True, 
                            timeout=10
                        )
                        output = result.stdout + result.stderr
                        if not output: output = "✅ Executed (No Output)"
                        conn.sendall(output.encode('utf-8'))
                    except Exception as e:
                        conn.sendall(f"❌ Error: {str(e)}".encode('utf-8'))
                else:
                    # --- AUTH FAIL ---
                    print(f"[SAT] 🛑 Auth Failed from {addr}")
                    conn.sendall(b"ERR: ACCESS DENIED")
            else:
                conn.sendall(b"ERR: INVALID FORMAT")
            
            conn.close()
        except Exception as e:
            print(f"[SAT] Command Listener Error: {e}")

def telemetry_sender(mlx):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', TELEM_PORT))
    server_socket.listen(1)
    print(f"[SAT] Telemetry Downlink Active on Port {TELEM_PORT}")

    frame = [0.0] * 768

    while True:
        print("[SAT] Waiting for Telemetry Link...")
        client_socket, addr = server_socket.accept()
        print(f"[SAT] Telemetry Connected: {addr}")

        try:
            while True:
                if mlx:
                    try: mlx.getFrame(frame)
                    except RuntimeError: continue
                else:
                    frame = [20.0] * 768

                binary_data = struct.pack('768f', *frame)
                client_socket.sendall(binary_data)
                time.sleep(0.20)

        except (BrokenPipeError, ConnectionResetError):
            print("[SAT] Telemetry Link Lost.")
            client_socket.close()
        except Exception as e:
            print(f"[SAT] Critical Error: {e}")
            client_socket.close()
            time.sleep(1)

if __name__ == '__main__':
    sensor = init_sensor()
    t_cmd = threading.Thread(target=command_listener, daemon=True)
    t_cmd.start()
    telemetry_sender(sensor)