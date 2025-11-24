#!/bin/bash

# Define paths
USER="flamesat"
WORKING_DIR="/home/$USER/flamesat/satellite"
# Point directly to the Python inside the virtual environment
PYTHON_EXEC="$WORKING_DIR/env/bin/python"
SCRIPT_PATH="$WORKING_DIR/tx_satellite.py"
SERVICE_FILE="/etc/systemd/system/flamesat.service"

echo "🛰️  Configuring FlameSat Auto-Boot System..."

# 1. Verify paths exist
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "❌ Error: Virtual environment not found at $PYTHON_EXEC"
    echo "   Did you create the 'env' folder?"
    exit 1
fi

# 2. Create Systemd Service File
echo "📝 Generating Service File..."
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=FlameSat Telemetry Transmitter
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$WORKING_DIR
ExecStart=$PYTHON_EXEC $SCRIPT_PATH
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# 3. Enable and Start
echo "⚡ Enabling Service..."
sudo systemctl daemon-reload
sudo systemctl enable flamesat.service
sudo systemctl restart flamesat.service

echo "✅ SUCCESS! FlameSat is now fully autonomous."
echo "   The transmitter will start automatically every time you power on the Pi."
echo "   View logs anytime with: journalctl -u flamesat -f"
