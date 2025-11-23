import socket
import json
import threading
from flask import Flask, jsonify, render_template_string

# --- CONFIGURATION ---
SATELLITE_IP = "192.168.40.20" # Your Pi's IP
SATELLITE_PORT = 5000          # Port Pi is transmitting on
WEB_PORT = 9876                # Port for Cloudflare to talk to

# Global variable to store the latest packet
latest_telemetry = {
    "status": "WAITING FOR SIGNAL...",
    "max": 0,
    "data": [0] * 768
}

app = Flask(__name__)

# --- THREAD 1: The Receiver (Listens to Pi) ---
def telemetry_receiver():
    global latest_telemetry
    while True:
        try:
            print(f"[GROUND] Connecting to Satellite at {SATELLITE_IP}...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SATELLITE_IP, SATELLITE_PORT))
            print("[GROUND] Link Established!")
            
            socket_file = client_socket.makefile()
            while True:
                line = socket_file.readline()
                if not line: break
                # Update the global data
                latest_telemetry = json.loads(line)
                
        except Exception as e:
            print(f"[GROUND] Link Error: {e}. Retrying in 5s...")
            time.sleep(5)

# --- THREAD 2: The Web Server (Talks to Cloudflare) ---

# 1. The API Endpoint (For raw data access)
@app.route('/api/telemetry')
def get_telemetry():
    return jsonify(latest_telemetry)

# 2. The Visual Dashboard (HTML/JS)
@app.route('/')
def dashboard():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FLAMESAT Mission Control</title>
        <style>
            body { font-family: monospace; background: #111; color: #0f0; text-align: center; }
            #status { font-size: 24px; font-weight: bold; margin: 20px; }
            .fire { color: red; animation: blink 1s infinite; }
            .nominal { color: #0f0; }
            @keyframes blink { 50% { opacity: 0; } }
            #heatmap { display: grid; grid-template-columns: repeat(32, 10px); gap: 1px; justify-content: center; }
            .pixel { width: 10px; height: 10px; background: #333; }
        </style>
    </head>
    <body>
        <h1>🛰️ FLAMESAT TELEMETRY LINK</h1>
        <div id="status">CONNECTING...</div>
        <div id="info">Max Temp: <span id="max_temp">0</span>°C</div>
        <br>
        <div id="heatmap"></div>

        <script>
            // Generate the 32x24 grid
            const grid = document.getElementById('heatmap');
            for(let i=0; i<768; i++) {
                let div = document.createElement('div');
                div.className = 'pixel';
                div.id = 'p'+i;
                grid.appendChild(div);
            }

            function update() {
                fetch('/api/telemetry')
                .then(r => r.json())
                .then(data => {
                    // Update Status Text
                    const stat = document.getElementById('status');
                    stat.innerText = "STATUS: " + data.status;
                    stat.className = data.status === "FIRE" ? "fire" : "nominal";
                    document.getElementById('max_temp').innerText = data.max;

                    // Update Heatmap Colors
                    const pixels = data.data;
                    const max = parseFloat(data.max);
                    const min = 20; // Baseline temp
                    
                    for(let i=0; i<768; i++) {
                        let temp = parseFloat(pixels[i]);
                        // Simple Heatmap Logic (Blue -> Red)
                        let intensity = (temp - min) / (max - min);
                        if(intensity < 0) intensity = 0;
                        if(intensity > 1) intensity = 1;
                        
                        let r = Math.floor(intensity * 255);
                        let b = Math.floor((1-intensity) * 255);
                        document.getElementById('p'+i).style.backgroundColor = `rgb(${r}, 0, ${b})`;
                    }
                });
            }
            setInterval(update, 500); // Poll every 500ms
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    # Start the receiver in background
    t = threading.Thread(target=telemetry_receiver)
    t.daemon = True
    t.start()
    
    # Start Web Server
    app.run(host='0.0.0.0', port=WEB_PORT)
