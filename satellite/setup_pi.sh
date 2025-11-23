#!/bin/bash
# Run this ON THE PI to setup the environment
echo "🛰️ Initializing FLAMESAT Environment..."
python3 -m venv env
source env/bin/activate
pip install adafruit-circuitpython-mlx90640 matplotlib numpy
echo "✅ Environment Ready. Run 'source env/bin/activate' then 'python tx_satellite.py'"
