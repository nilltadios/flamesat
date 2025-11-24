#!/bin/bash

# 1. Identify where this script is living
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit

# 2. Configuration
SAT_HOST="flamesat.local"
SAT_PORT=5000
LOG_DIR="logs"

mkdir -p "$LOG_DIR"

echo "========================================"
echo "   🔥 FLAMESAT MISSION CONTROL v1.2   "
echo "========================================"

# 3. UPLINK CHECK (The "Command" Phase)
echo "📡 Attempting to acquire satellite signal..."

# Use netcat (nc) to check if the satellite is listening on port 5000
# -z = scan only, -w 2 = wait max 2 seconds
if nc -z -w 2 "$SAT_HOST" "$SAT_PORT"; then
    echo "   ✅ UPLINK ESTABLISHED: Satellite is Online and Listening."
else
    echo "   ⚠️  WARNING: Satellite Unreachable."
    echo "      - Is the Pi powered on?"
    echo "      - Is the 'flamesat' service running?"
    echo "      - Attempting to launch anyway (Telemetry may be offline)..."
fi

echo "🚀 Initializing Ground Systems..."

# 4. Start Cloudflare Tunnel
nohup cloudflared tunnel --config flame_tunnel/config_flame.yml run > "$LOG_DIR/flame_tunnel.log" 2>&1 &
TUNNEL_PID=$!
echo "   🔹 Tunnel Active (PID: $TUNNEL_PID)"

# 5. Start Ground Server
# We use the system python here (assuming dependencies are installed globally or use a venv if you have one on ground)
nohup python3 ground_server.py > "$LOG_DIR/flame_server.log" 2>&1 &
SERVER_PID=$!
echo "   🔹 Server Active (PID: $SERVER_PID)"

# 6. Save PIDs
echo "$TUNNEL_PID" > "$LOG_DIR/mission.pids"
echo "$SERVER_PID" >> "$LOG_DIR/mission.pids"

echo "----------------------------------------"
echo "✅ MISSION LIVE"
echo "📊 Dashboard: https://flamedata.nillsite.com"
echo "📝 Logs:      $SCRIPT_DIR/$LOG_DIR/"
echo "----------------------------------------"
