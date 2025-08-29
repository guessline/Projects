# ML Bridge for MetaTrader 5 on Linux

This is a Linux-compatible version of the Python ML Bridge script for MetaTrader 5 trading signals.

## Features

- **Robust file reading** with multiple encoding support
- **Atomic file writing** to prevent corruption
- **Signal generation** based on EMA crossover strategy
- **Linux-optimized** file handling and permissions
- **Wine/MT5 compatibility** checks
- **Automatic retry mechanism** for file operations

## Installation

### Prerequisites

1. **Python 3.6+** installed
2. **Wine** (if running MetaTrader 5 on Linux)
3. **MetaTrader 5** installed via Wine

### Setup

1. Install Wine (if not already installed):
```bash
sudo apt-get update
sudo apt-get install wine wine32 wine64
```

2. Install MetaTrader 5 through Wine:
```bash
# Download MT5 installer from broker
wine mt5setup.exe
```

3. Configure the script paths:
   - Edit `ml_bridge_linux.py`
   - Update `FEAT` and `PRED` paths to match your MT5 installation

## Configuration

The script supports three path configurations:

### Option 1: Default Wine Prefix
```python
FEAT = os.path.expanduser("~/.wine/drive_c/users/$USER/Application Data/MetaQuotes/Terminal/Common/Files/features_bt.csv")
PRED = os.path.expanduser("~/.wine/drive_c/users/$USER/Application Data/MetaQuotes/Terminal/Common/Files/prediction_bt.txt")
```

### Option 2: Custom Wine Prefix
```python
WINE_PREFIX = os.path.expanduser("~/.mt5")
FEAT = f"{WINE_PREFIX}/drive_c/users/{os.environ['USER']}/Application Data/MetaQuotes/Terminal/Common/Files/features_bt.csv"
```

### Option 3: Local Testing (Default)
```python
FEAT = "/workspace/mt_files/features_bt.csv"
PRED = "/workspace/mt_files/prediction_bt.txt"
```

## Usage

### Testing the Script

1. Set up test environment:
```bash
python3 setup_test_environment.py
```

2. Run the ML Bridge:
```bash
python3 ml_bridge_linux.py
```

3. The script will:
   - Monitor the features file for changes
   - Parse trading data (timestamp, close, EMA, ATR)
   - Generate trading signals (BUY/SELL/NONE)
   - Write predictions to the output file

### Production Use

1. Ensure MT5 is running under Wine
2. Configure correct file paths in the script
3. Run the bridge:
```bash
python3 ml_bridge_linux.py
```

4. The script will continuously monitor for new data from MT5

## File Format

### Input (features_bt.csv)
```
DateTime;Close;EMA;ATR
2024.01.15 14:30;1.1050;1.1040;0.0015
```

### Output (prediction_bt.txt)
```
BUY;2024.01.15 14:30
```

## Signal Logic

- **BUY**: When Close > EMA × 1.001
- **SELL**: When Close < EMA × 0.999
- **NONE**: When price is too close to EMA (within 0.1%)

## Parameters

- `POLL_INTERVAL`: 0.1 seconds (file check frequency)
- `WRITE_RETRIES`: 5 attempts (for locked files)
- `COOLDOWN_SEC`: 0.5 seconds (pause after writing)
- `EXPECTED_FIELDS`: 4 (DateTime;Close;EMA;ATR)

## Troubleshooting

### Permission Denied
```bash
# Fix directory permissions
chmod 755 /path/to/mt_files
```

### Wine Path Issues
```bash
# Find Wine prefix
echo $WINEPREFIX
# or default
ls ~/.wine
```

### MT5 File Locations
```bash
# Find MT5 data directory
find ~/.wine -name "Common" -type d 2>/dev/null | grep MetaQuotes
```

## Features Comparison

| Feature | Windows Version | Linux Version |
|---------|----------------|---------------|
| Encodings | Multiple Windows encodings | UTF-8, ASCII focused |
| File Operations | Windows file locking handling | Linux atomic operations |
| Path Format | Windows backslash paths | Unix forward slash paths |
| Permissions | Windows ACL | Unix chmod |
| Wine Support | N/A | Built-in checks |

## License

This script is provided as-is for trading automation purposes.