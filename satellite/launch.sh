#!/bin/bash

# 1. Move to the Mission Control Folder
cd /home/flamesat/flamesat/satellite

# 2. Activate the Python Environment
source env/bin/activate

# 3. Run the Flight Software
echo "🚀 FLAMESAT LAUNCH SEQUENCE INITIATED..."
python main.py

# 4. Keep window open if it crashes (so you can see errors)
echo ""
read -p "Mission Ended. Press Enter to close terminal..."
