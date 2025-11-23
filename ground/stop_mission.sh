#!/bin/bash

# Identify where this script is living
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/logs/mission.pids"

if [ -f "$PID_FILE" ]; then
    echo "🛑 Shutting down Mission Control..."

    # Read PIDs from local file and kill them
    while read pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "   🔻 Terminated Process $pid"
        else
            echo "   ⚠️ Process $pid not found (already dead?)"
        fi
    done < "$PID_FILE"

    # Clean up
    rm "$PID_FILE"
    echo "✅ Systems Offline."
else
    echo "⚠️ No active mission found (checked $PID_FILE)."
fi
