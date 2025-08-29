#!/usr/bin/env python3
"""
Configuration file for MT5 Trading Bridge

This file contains all configurable parameters for the trading bridge.
Modify these values according to your trading setup and requirements.
"""

import os
from pathlib import Path

# ========= PATH CONFIGURATION =========
# Default data directory (can be overridden via environment variables)
DEFAULT_DATA_DIR = Path.home() / "mt5_data"

# Input features file path
FEATURES_FILE = os.getenv("MT5_FEATURES_PATH", str(DEFAULT_DATA_DIR / "features_bt.csv"))

# Output predictions file path  
PREDICTIONS_FILE = os.getenv("MT5_PREDICTION_PATH", str(DEFAULT_DATA_DIR / "prediction_bt.txt"))

# ========= TIMING CONFIGURATION =========
# Polling interval in seconds (how often to check for new data)
POLL_INTERVAL = 0.1

# Cooldown period after writing predictions (allows MT5 to read the file)
COOLDOWN_SEC = 0.5

# Number of retry attempts for file operations
WRITE_RETRIES = 5

# ========= DATA FORMAT CONFIGURATION =========
# Expected number of fields in features CSV: "YYYY.MM.DD HH:MM;close;ema;atr"
EXPECTED_FIELDS = 4

# Timestamp format in the features file
TIMESTAMP_FORMAT = "%Y.%m.%d %H:%M"

# ========= SIGNAL GENERATION CONFIGURATION =========
# Minimum price difference threshold (to avoid noise)
MIN_PRICE_DIFF = 0.01

# Buy signal threshold (close must be this much above EMA)
BUY_THRESHOLD = 1.001  # 0.1% above EMA

# Sell signal threshold (close must be this much below EMA)  
SELL_THRESHOLD = 0.999  # 0.1% below EMA

# ========= ERROR HANDLING CONFIGURATION =========
# Maximum consecutive errors before shutting down
MAX_CONSECUTIVE_ERRORS = 10

# Encodings to try when reading files (in order of preference)
FILE_ENCODINGS = ['ascii', 'utf-8', 'utf-16-le', 'utf-16', 'cp1251', 'latin-1']

# Number of reading attempts for each file
READ_ATTEMPTS = 3

# ========= LOGGING CONFIGURATION =========
# Enable verbose logging
VERBOSE_LOGGING = True

# Log file path (None to disable file logging)
LOG_FILE = None  # str(DEFAULT_DATA_DIR / "mt5_bridge.log")

# ========= SAMPLE DATA CONFIGURATION =========
# Sample data to create when features file doesn't exist
SAMPLE_FEATURES_DATA = """2024.01.15 09:30;1.0950;1.0945;0.0015
2024.01.15 09:31;1.0955;1.0947;0.0016
2024.01.15 09:32;1.0960;1.0949;0.0017
2024.01.15 09:33;1.0952;1.0950;0.0015
2024.01.15 09:34;1.0958;1.0951;0.0016
"""