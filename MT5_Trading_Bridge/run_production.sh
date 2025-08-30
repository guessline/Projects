#!/bin/bash
# Production MT5 Bridge Launcher - Optimized Version

echo "🚀 Starting MT5 Trading Bridge - Production Version"
echo "=================================================="

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# Ensure minimum Python version
if [[ $(echo "$PYTHON_VERSION >= 3.8" | bc -l) -eq 1 ]]; then
    echo "✅ Python version compatible with async features"
    BRIDGE_SCRIPT="mt5_bridge_production.py"
else
    echo "⚠️  Using fallback version for older Python"
    BRIDGE_SCRIPT="mt5_bridge.py"
fi

# Create data directory
mkdir -p ~/mt5_data

# Set optimal environment variables
export PYTHONUNBUFFERED=1
export MT5_FEATURES_PATH="$HOME/mt5_data/features_bt.csv"
export MT5_PREDICTION_PATH="$HOME/mt5_data/prediction_bt.txt"

echo "Data directory: ~/mt5_data"
echo "Using script: $BRIDGE_SCRIPT"
echo "=================================================="

# Run with enhanced error handling
python3 "$BRIDGE_SCRIPT" 2>&1 | tee ~/mt5_data/bridge_$(date +%Y%m%d_%H%M%S).log