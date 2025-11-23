#!/bin/bash

# 1. Identify where this script is living (makes it portable)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit

# 2. Create a local directory for logs and PIDs if it doesn't exist
mkdir -p logs

echo "🚀 Initializing Ground Station..."

# 3. Start Cloudflare Tunnel (Silent)
# Note: Config path is relative to SCRIPT_DIR
nohup cloudflared tunnel --config flame_tunnel/config_flame.yml run > logs/flame_tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "   ✅ Tunnel Active (PID: $TUNNEL_PID)"

# 4. Start Ground Server (Silent)
nohup python3 ground_server.py > logs/flame_server.log 2>&1 &
SERVER_PID=$!
echo "   ✅ Server Active (PID: $SERVER_PID)"

# 5. Save PIDs to local file
echo "$TUNNEL_PID" > logs/mission.pids
echo "$SERVER_PID" >> logs/mission.pids

echo "📡 Mission Control is LIVE at https://flamedata.nillsite.com"
echo "   (Logs available in $SCRIPT_DIR/logs/)"
