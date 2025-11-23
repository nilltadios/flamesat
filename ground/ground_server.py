import socket
import json
import threading
import time
import logging
from flask import Flask, jsonify, render_template_string, request

# --- CONFIGURATION ---
SATELLITE_HOSTNAME = "flamesat.local"
KNOWN_IPS = ["192.168.40.20", "10.54.254.151", "10.42.0.159"]
SATELLITE_PORT = 5000
WEB_PORT = 9876

# --- SILENCE LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

latest_telemetry = {
    "status": "SEARCHING...",
    "max": 0,
    "data": [0] * 768
}

app = Flask(__name__)

def find_satellite():
    try:
        ip = socket.gethostbyname(SATELLITE_HOSTNAME)
        return ip
    except:
        pass
    for ip in KNOWN_IPS:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            s.connect((ip, SATELLITE_PORT))
            s.close()
            return ip
        except:
            pass
    return None

def telemetry_receiver():
    global latest_telemetry
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
                latest_telemetry = json.loads(line)
        except:
            client_socket.close()
            time.sleep(1)

@app.route('/api/telemetry')
def get_telemetry():
    return jsonify(latest_telemetry)

@app.route('/')
def dashboard():
    host_url = request.host_url.rstrip('/')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FLAMESAT CMD</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <style>
            :root {{ --primary: #0f0; --alert: #f00; --bg: #050505; --panel: #111; }}
            body {{ 
                font-family: 'Share Tech Mono', monospace; 
                background-color: var(--bg); 
                color: var(--primary); 
                margin: 0; padding: 20px;
                display: flex; flex-direction: column; align-items: center;
            }}
            
            /* CRT Scanline Effect */
            body::before {{
                content: " ";
                display: block;
                position: absolute; top: 0; left: 0; bottom: 0; right: 0;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
                z-index: 2; background-size: 100% 2px, 3px 100%; pointer-events: none;
            }}

            .container {{
                width: 100%; max-width: 800px;
                border: 1px solid #333; padding: 20px;
                box-shadow: 0 0 20px rgba(0, 255, 0, 0.1);
                background: var(--panel); z-index: 1;
            }}

            header {{ display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
            h1 {{ margin: 0; font-size: 24px; letter-spacing: 2px; }}
            
            .status-box {{ font-size: 18px; }}
            .nominal {{ color: var(--primary); }}
            .fire {{ color: var(--alert); animation: blink 0.5s infinite; text-shadow: 0 0 10px red; }}
            @keyframes blink {{ 50% {{ opacity: 0; }} }}

            .telemetry-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
            .metric {{ background: #000; padding: 10px; border: 1px solid #333; text-align: center; }}
            .metric-label {{ font-size: 12px; color: #666; display: block; margin-bottom: 5px; }}
            .metric-value {{ font-size: 32px; }}

            /* Heatmap Container */
            #heatmap-container {{ 
                position: relative; 
                width: 100%; 
                aspect-ratio: 4/3; 
                background: #000; 
                border: 1px solid #333; 
            }}
            #heatmap {{ 
                display: grid; 
                grid-template-columns: repeat(32, 1fr); 
                width: 100%; height: 100%; 
            }}
            .pixel {{ width: 100%; height: 100%; }}

            /* API Terminal */
            .terminal {{ 
                margin-top: 30px; text-align: left; 
                border: 1px solid #444; background: #000; padding: 10px; 
            }}
            .terminal-header {{ color: #666; font-size: 12px; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px; }}
            code {{ color: #aaa; display: block; word-break: break-all; }}
            .cmd-prompt {{ color: #0f0; margin-right: 10px; }} user@ground:~$
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>FLAMESAT_01</h1>
                <div id="clock">--:--:-- UTC</div>
            </header>

            <div class="telemetry-grid">
                <div class="metric">
                    <span class="metric-label">SYSTEM STATUS</span>
                    <div id="status" class="nominal">WAITING</div>
                </div>
                <div class="metric">
                    <span class="metric-label">MAX TEMP</span>
                    <div id="max_temp" class="metric-value">0.0°C</div>
                </div>
            </div>

            <div id="heatmap-container">
                <div id="heatmap"></div>
            </div>

            <div class="terminal">
                <div class="terminal-header">/// API ACCESS LINK ///</div>
                <code><span class="cmd-prompt">user@ground:~$</span> curl -s {host_url}/api/telemetry | jq</code>
            </div>
        </div>

        <script>
            // Clock
            setInterval(() => {{
                document.getElementById('clock').innerText = new Date().toISOString().split('T')[1].split('.')[0] + ' UTC';
            }}, 1000);

            // Init Grid
            const grid = document.getElementById('heatmap');
            for(let i=0; i<768; i++) {{
                let div = document.createElement('div');
                div.className = 'pixel';
                div.id = 'p'+i;
                grid.appendChild(div);
            }}

            function update() {{
                fetch('/api/telemetry')
                .then(r => r.json())
                .then(data => {{
                    const stat = document.getElementById('status');
                    stat.innerText = data.status;
                    
                    if(data.status.includes("FIRE")) {{
                        stat.className = "fire";
                        document.documentElement.style.setProperty('--primary', '#f00');
                    }} else {{
                        stat.className = "nominal";
                        document.documentElement.style.setProperty('--primary', '#0f0');
                    }}
                    
                    document.getElementById('max_temp').innerText = data.max + "°C";

                    const pixels = data.data;
                    const max = parseFloat(data.max) || 40;
                    const min = 20; 
                    
                    for(let i=0; i<768; i++) {{
                        let val = parseFloat(pixels[i]);
                        let intensity = (val - min) / (max - min);
                        intensity = Math.max(0, Math.min(1, intensity));
                        
                        // Smooth Interpolation (Black -> Blue -> Purple -> Red -> Yellow)
                        let r = Math.floor(intensity * 255);
                        let g = intensity > 0.8 ? Math.floor((intensity-0.8)*5 * 255) : 0;
                        let b = Math.floor((1-intensity) * 100);
                        
                        document.getElementById('p'+i).style.backgroundColor = `rgb(${{r}}, ${{g}}, ${{b}})`;
                    }}
                }});
            }}
            setInterval(update, 500);
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    t = threading.Thread(target=telemetry_receiver)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=WEB_PORT)