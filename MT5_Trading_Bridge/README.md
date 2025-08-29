# MT5 Trading Bridge - Linux Version

A robust Python bridge between MetaTrader 5 (MT5) and Machine Learning models for algorithmic trading. This bridge reads trading features from CSV files and generates trading signals in real-time.

## 🚀 Features

- **Real-time Processing**: Monitors feature files and generates signals instantly
- **Robust File Handling**: Multiple encoding support and atomic file operations
- **Signal Generation**: Simple EMA-based trading signals (BUY/SELL/NONE)
- **Linux Compatible**: Adapted from Windows version with proper path handling
- **Error Recovery**: Comprehensive error handling with automatic recovery
- **Configurable**: Easy to customize via configuration file

## 📁 Project Structure

```
MT5_Trading_Bridge/
├── mt5_bridge.py          # Main bridge application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
└── data/                 # Data directory (created automatically)
    ├── features_bt.csv   # Input: trading features
    └── prediction_bt.txt # Output: trading signals
```

## 🔧 Installation

1. **Clone or download the project**
   ```bash
   cd /workspace/MT5_Trading_Bridge
   ```

2. **Install dependencies (optional)**
   ```bash
   pip install -r requirements.txt
   ```

3. **Make the script executable**
   ```bash
   chmod +x mt5_bridge.py
   ```

## ⚙️ Configuration

### Environment Variables

You can override default paths using environment variables:

```bash
export MT5_FEATURES_PATH="/custom/path/features_bt.csv"
export MT5_PREDICTION_PATH="/custom/path/prediction_bt.txt"
```

### Configuration File

Edit `config.py` to customize:

- **File paths**: Input and output file locations
- **Timing**: Polling intervals and cooldown periods
- **Signal parameters**: Trading thresholds and conditions
- **Error handling**: Retry attempts and error limits

## 🚀 Usage

### Basic Usage

```bash
python3 mt5_bridge.py
```

### Background Execution

```bash
nohup python3 mt5_bridge.py > bridge.log 2>&1 &
```

### With Custom Configuration

```bash
MT5_FEATURES_PATH="/path/to/features.csv" python3 mt5_bridge.py
```

## 📊 Data Format

### Input Features File (`features_bt.csv`)

Expected format (semicolon-separated):
```
YYYY.MM.DD HH:MM;close_price;ema_value;atr_value
```

Example:
```
2024.01.15 09:30;1.0950;1.0945;0.0015
2024.01.15 09:31;1.0955;1.0947;0.0016
2024.01.15 09:32;1.0960;1.0949;0.0017
```

### Output Predictions File (`prediction_bt.txt`)

Format:
```
SIGNAL;TIMESTAMP
```

Examples:
```
BUY;2024.01.15 09:30
SELL;2024.01.15 09:31
NONE;2024.01.15 09:32
```

## 🧠 Signal Logic

The bridge uses a simple EMA-based strategy:

- **BUY Signal**: `close_price > ema * 1.001` (0.1% above EMA)
- **SELL Signal**: `close_price < ema * 0.999` (0.1% below EMA)  
- **NONE Signal**: Price too close to EMA (within 0.01)

You can modify these thresholds in `config.py`.

## 🔍 Monitoring

The bridge provides real-time status updates:

```
✓ Read success with ascii: 2024.01.15 09:30;1.0950;1.0945;0.0015...
🔵 [2024.01.15 09:30] close=1095 ema=1095 atr=1.5 → BUY
✓ SIGNAL: BUY for 2024.01.15 09:30
```

Status indicators:
- 🔵 BUY signal
- 🔴 SELL signal  
- ⚪ No signal
- ✓ Successful operations
- ✗ Errors or failures
- ⏳ Waiting states

## 🛠️ Troubleshooting

### Common Issues

1. **File Not Found Errors**
   ```bash
   # Check if data directory exists
   ls -la ~/mt5_data/
   
   # Create if missing
   mkdir -p ~/mt5_data/
   ```

2. **Permission Errors**
   ```bash
   # Fix permissions
   chmod 755 ~/mt5_data/
   chmod 644 ~/mt5_data/*.csv
   ```

3. **Encoding Issues**
   The bridge automatically tries multiple encodings:
   - ASCII (preferred)
   - UTF-8
   - UTF-16
   - CP1251 (Cyrillic)
   - Latin-1

### Debugging

Enable verbose output and check logs:

```bash
python3 mt5_bridge.py 2>&1 | tee debug.log
```

## 🔒 Security Considerations

- The bridge only reads from features file and writes to predictions file
- No network connections or external dependencies
- Uses atomic file operations to prevent corruption
- Automatic cleanup of temporary files

## 🚀 Performance

- **Polling Interval**: 0.1 seconds (configurable)
- **Memory Usage**: Minimal (< 10MB typical)
- **CPU Usage**: Very low (< 1% on modern systems)
- **File I/O**: Optimized with atomic operations

## 🔄 Integration with MT5

### MT5 Expert Advisor Integration

```mql5
// Read signals in MT5 EA
string filename = "prediction_bt.txt";
string signal = "";
string timestamp = "";

// Read latest signal
int handle = FileOpen(filename, FILE_READ|FILE_TXT);
if(handle != INVALID_HANDLE) {
    string line = FileReadString(handle);
    string parts[];
    StringSplit(line, ';', parts);
    if(ArraySize(parts) >= 2) {
        signal = parts[0];
        timestamp = parts[1];
    }
    FileClose(handle);
}

// Execute trades based on signal
if(signal == "BUY") {
    // Open buy position
} else if(signal == "SELL") {
    // Open sell position
}
```

## 📈 Extending the Bridge

### Adding New Indicators

1. Modify `parse_features_robust()` to handle additional fields
2. Update `EXPECTED_FIELDS` in config
3. Extend `make_signal()` function with new logic

### Custom Signal Strategies

```python
def make_signal_advanced(close, ema, atr, rsi=None):
    """Advanced signal logic with multiple indicators"""
    # Your custom logic here
    if rsi and rsi < 30 and close > ema:
        return "BUY"
    elif rsi and rsi > 70 and close < ema:
        return "SELL"
    return "NONE"
```

## 📝 Changelog

### Version 2.0.0 (Linux)
- ✅ Linux compatibility
- ✅ Configurable paths via environment variables
- ✅ Enhanced error handling
- ✅ Automatic data directory creation
- ✅ Sample data generation
- ✅ Improved documentation

### Version 1.0.0 (Windows)
- ✅ Basic MT5 bridge functionality
- ✅ EMA-based signal generation
- ✅ Robust file handling
- ✅ Atomic file operations

## 📄 License

This project is open source. Feel free to modify and distribute according to your needs.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Verify file permissions and paths
4. Test with sample data first

---

**Note**: This bridge is designed for educational and research purposes. Always test thoroughly before using in live trading environments.