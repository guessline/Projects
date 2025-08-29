#!/bin/bash
# MT5 Trading Bridge Startup Script

echo "Starting MT5 Trading Bridge..."
echo "================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if the bridge script exists
if [ ! -f "mt5_bridge.py" ]; then
    echo "Error: mt5_bridge.py not found in current directory"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p ~/mt5_data

# Run the bridge
echo "Running bridge with PID: $$"
echo "Data directory: ~/mt5_data"
echo "Press Ctrl+C to stop"
echo "================================"

python3 mt5_bridge.py