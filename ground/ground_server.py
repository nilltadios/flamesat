import socket
import json
import threading
import time
import logging
import smtplib
import os
from email.mime.text import MIMEText
from flask import Flask, jsonify, render_template_string, request

# --- LOAD SECRETS ---
# Load credentials from the ignored JSON file
SECRETS_FILE = "secrets.json"
try:
    with open(SECRETS_FILE) as f:
        secrets = json.load(f)
        EMAIL_SENDER = secrets["email_sender"]
        EMAIL_PASSWORD = secrets["email_password"]
        EMAIL_RECEIVER = secrets["email_receiver"]
except FileNotFoundError:
    print(f"❌ ERROR: {SECRETS_FILE} not found! Create it to enable alerts.")
    EMAIL_SENDER = None

# --- CONFIGURATION ---
SATELLITE_HOSTNAME = "flamesat.local"
KNOWN_IPS = ["192.168.40.20", "10.54.254.151", "10.42.0.159"]
SATELLITE_PORT = 5000
WEB_PORT = 9876
ALERT_COOLDOWN = 60 

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

latest_telemetry = {"status": "SEARCHING...", "max": 0, "data": [0] * 768}
last_alert_time = 0 # Timestamp of last email

app = Flask(__name__)

def send_email_thread(temp):
    """Runs in background to send email"""
    try:
        msg = MIMEText(f"EMERGENCY ALERT\n\nFLAMESAT has detected a thermal anomaly.\nMax Temperature: {temp}°C\n\nView Telemetry: https://flamedata.nillsite.com")
        msg['Subject'] = f"🔥 FLAMESAT ALERT: {temp}°C DETECTED"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[WATCHDOG] ✅ Alert Email Sent for {temp}°C.")
    except Exception as e:
        print(f"[WATCHDOG] ❌ Email Failed: {e}")

def find_satellite():
    try: return socket.gethostbyname(SATELLITE_HOSTNAME)
    except: pass
    for ip in KNOWN_IPS:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2); s.connect((ip, SATELLITE_PORT)); s.close()
            return ip
        except: pass
    return None

def telemetry_receiver():
    global latest_telemetry, last_alert_time
    
    while True:
        target_ip = find_satellite()
        if not target_ip:
            latest_telemetry["status"] = "OFFLINE - SCANNING..."
            time.sleep(3)
            continue

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10)
            client_socket.connect((target_ip, SATELLITE_PORT))
            
            socket_file = client_socket.makefile()
            while True:
                line = socket_file.readline()
                if not line: break
                
                data = json.loads(line)
                latest_telemetry = data
                
                # --- WATCHDOG LOGIC (FIXED) ---
                if data['status'] == "FIRE" and EMAIL_SENDER:
                    current_time = time.time()
                    
                    # Check cooldown
                    if (current_time - last_alert_time) > ALERT_COOLDOWN:
                        # 1. UPDATE TIMER IMMEDIATELY (Prevents Spam)
                        last_alert_time = current_time
                        print(f"\n[WATCHDOG] ⚠️ Fire Detected ({data['max']}°C). Dispatching Alert...")
                        
                        # 2. Start Thread
                        threading.Thread(target=send_email_thread, args=(data['max'],)).start()

        except:
            client_socket.close()
            time.sleep(1)

@app.route('/api/telemetry')
def get_telemetry():
    return jsonify(latest_telemetry)

@app.route('/')
def dashboard():
    # (Keep your existing Sci-Fi HTML code here)
    # I am truncating it to save space, but DO NOT DELETE IT from your file.
    # Just ensure this function returns the render_template_string(html)
    # ...
    return "<html>...Your Sci-Fi HTML Code...</html>" 

if __name__ == '__main__':
    t = threading.Thread(target=telemetry_receiver)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=WEB_PORT)