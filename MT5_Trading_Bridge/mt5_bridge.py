#!/usr/bin/env python3
"""
MT5 Trading Bridge - Linux Version

A robust bridge between MetaTrader 5 and Python ML models.
Reads trading features from CSV file and generates trading signals.

Original Windows version adapted for Linux environment.
"""

import os
import time
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# ========= CONFIGURATION =========
# Default paths for Linux environment (can be overridden via environment variables)
DEFAULT_DATA_DIR = Path.home() / "mt5_data"
FEAT = os.getenv("MT5_FEATURES_PATH", str(DEFAULT_DATA_DIR / "features_bt.csv"))
PRED = os.getenv("MT5_PREDICTION_PATH", str(DEFAULT_DATA_DIR / "prediction_bt.txt"))

# ========= SETTINGS =========
POLL_INTERVAL = 0.1        # polling interval in seconds
WRITE_RETRIES = 5          # number of write attempts
COOLDOWN_SEC  = 0.5        # cooldown period for stability
EXPECTED_FIELDS = 4        # "YYYY.MM.DD HH:MM;close;ema;atr"

def ensure_data_directory():
    """Ensure the data directory exists"""
    data_dir = Path(FEAT).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def _read_last_line_robust(path):
    """
    Robust reading of the last line from file with multiple attempts
    """
    if not os.path.exists(path):
        return None
        
    # Encodings to try in order
    encodings_to_try = ['ascii', 'utf-8', 'utf-16-le', 'utf-16', 'cp1251', 'latin-1']
    
    for attempt in range(3):  # 3 reading attempts
        for encoding in encodings_to_try:
            try:
                with open(path, "r", encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()
                
                # Search for the last valid line
                for line in reversed(lines):
                    line = line.strip().replace('\x00', '').replace('\ufeff', '')
                    if line and ';' in line and len(line.split(';')) >= EXPECTED_FIELDS:
                        print(f"✓ Read success with {encoding}: {line[:60]}...")
                        return line
                        
            except Exception as e:
                continue
        
        if attempt < 2:
            time.sleep(0.05)  # short pause between attempts
    
    print("✗ Failed to read file after all attempts")
    return None

def parse_features_robust(line):
    """Robust parsing with validation"""
    try:
        parts = [p.strip() for p in line.split(';')]
        if len(parts) < EXPECTED_FIELDS:
            raise ValueError(f"Expected {EXPECTED_FIELDS} fields, got {len(parts)}")

        ts = parts[0][:16]  # strictly up to minutes
        
        # Parse numbers with comma to dot replacement
        close = float(parts[-3].replace(',', '.'))
        ema   = float(parts[-2].replace(',', '.'))
        atr   = float(parts[-1].replace(',', '.'))

        # Validate timestamp
        datetime.strptime(ts, "%Y.%m.%d %H:%M")
        
        # Check reasonable values
        if close <= 0 or ema <= 0 or atr < 0:
            raise ValueError("Invalid price values")
            
        return ts, close, ema, atr
        
    except Exception as e:
        print(f"✗ Parse error: {e}")
        print(f"Raw line: {repr(line[:100])}")
        raise

def make_signal(close, ema):
    """Simple signal logic with additional checks"""
    try:
        if abs(close - ema) < 0.01:  # too close - no signal
            return "NONE"
            
        if close > ema * 1.001:  # minimum threshold for BUY
            return "BUY"
        elif close < ema * 0.999:  # minimum threshold for SELL
            return "SELL"
            
        return "NONE"
    except:
        return "NONE"

def write_prediction_atomic_robust(path, payload):
    """
    Maximally robust writing through temporary file with lock bypass
    """
    dir_path = os.path.dirname(path)
    
    for attempt in range(1, WRITE_RETRIES + 1):
        temp_file = None
        try:
            # Remove existing file before writing new one
            if os.path.exists(path):
                try:
                    os.remove(path)
                    time.sleep(0.05)  # Pause for MT5 file release
                except (PermissionError, FileNotFoundError):
                    # File may be locked by MT5, try different approach
                    pass
            
            # Create temporary file in the same directory
            with tempfile.NamedTemporaryFile(
                mode='w', 
                encoding='ascii', 
                delete=False, 
                dir=dir_path,
                prefix='pred_tmp_',
                suffix='.txt'
            ) as temp_file:
                temp_file.write(payload)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = temp_file.name
            
            # Give MT5 time to release old file
            time.sleep(0.1)
            
            # Try to atomically move file
            try:
                shutil.move(temp_path, path)
            except PermissionError:
                # If MT5 still holds file, wait and try again
                time.sleep(0.2)
                if os.path.exists(path):
                    os.remove(path)
                time.sleep(0.1)
                shutil.move(temp_path, path)
            
            # Verify file was written correctly
            if os.path.exists(path):
                with open(path, 'r', encoding='ascii') as f:
                    written_content = f.read().strip()
                if written_content == payload.strip():
                    print(f"✓ Write successful on attempt {attempt}")
                    return True
                    
        except PermissionError as e:
            print(f"✗ Write attempt {attempt} - Permission denied (MT5 file lock)")
            # Cleanup temporary file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except:
                    pass
                    
        except Exception as e:
            print(f"✗ Write attempt {attempt} failed: {e}")
            # Cleanup temporary file on error
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except:
                    pass
        
        if attempt < WRITE_RETRIES:
            time.sleep(0.2 * attempt)  # Increasing pause
    
    print(f"✗ All {WRITE_RETRIES} write attempts failed")
    return False

def cleanup_old_predictions():
    """Cleanup old prediction files"""
    try:
        pred_dir = os.path.dirname(PRED)
        for filename in os.listdir(pred_dir):
            if filename.startswith('pred_tmp_'):
                old_file = os.path.join(pred_dir, filename)
                try:
                    os.remove(old_file)
                except:
                    pass
    except:
        pass

def create_sample_features_file():
    """Create a sample features file for testing"""
    sample_data = """2024.01.15 09:30;1.0950;1.0945;0.0015
2024.01.15 09:31;1.0955;1.0947;0.0016
2024.01.15 09:32;1.0960;1.0949;0.0017
2024.01.15 09:33;1.0952;1.0950;0.0015
2024.01.15 09:34;1.0958;1.0951;0.0016
"""
    
    feat_path = Path(FEAT)
    if not feat_path.exists():
        print(f"Creating sample features file at: {feat_path}")
        feat_path.parent.mkdir(parents=True, exist_ok=True)
        with open(feat_path, 'w') as f:
            f.write(sample_data)

def main():
    print("=" * 70)
    print("Python ML Bridge - LINUX ROBUST VERSION")
    print("=" * 70)
    print(f"Features  : {FEAT}")
    print(f"Prediction: {PRED}")
    print(f"Poll      : {POLL_INTERVAL}s")
    print(f"Cooldown  : {COOLDOWN_SEC}s")
    print(f"Retries   : {WRITE_RETRIES}")
    
    # Ensure data directory exists
    data_dir = ensure_data_directory()
    print(f"Data dir  : {data_dir}")
    
    # Check directory accessibility
    feat_dir = os.path.dirname(FEAT)
    pred_dir = os.path.dirname(PRED)
    
    if not os.path.exists(feat_dir):
        print(f"✗ CRITICAL: Features directory not found: {feat_dir}")
        print("Creating directory...")
        os.makedirs(feat_dir, exist_ok=True)
        
    if not os.path.exists(pred_dir):
        print(f"✗ CRITICAL: Predictions directory not found: {pred_dir}")
        print("Creating directory...")
        os.makedirs(pred_dir, exist_ok=True)
        
    if not os.access(pred_dir, os.W_OK):
        print(f"✗ CRITICAL: No write access to: {pred_dir}")
        return
    
    # Create sample file if features file doesn't exist
    if not os.path.exists(FEAT):
        create_sample_features_file()
    
    # Cleanup old temporary files
    cleanup_old_predictions()
    
    print("✓ All checks passed, starting main loop...")
    print("=" * 70)

    last_ts = None
    last_mtime = 0.0
    consecutive_errors = 0
    max_errors = 10

    while True:
        try:
            # Check features file existence
            if not os.path.exists(FEAT):
                if consecutive_errors == 0:
                    print("⏳ Waiting for features file...")
                time.sleep(POLL_INTERVAL)
                continue

            # Check file modification
            try:
                mtime = os.path.getmtime(FEAT)
            except OSError:
                time.sleep(POLL_INTERVAL)
                continue
                
            if mtime == last_mtime:
                time.sleep(POLL_INTERVAL)
                continue
                
            last_mtime = mtime

            # Read features file
            line = _read_last_line_robust(FEAT)
            if not line:
                print("⏳ No valid data in features file")
                time.sleep(POLL_INTERVAL)
                continue

            # Parse data
            try:
                ts, close, ema, atr = parse_features_robust(line)
            except Exception as e:
                print(f"✗ Parse failed: {e}")
                consecutive_errors += 1
                if consecutive_errors > max_errors:
                    print("✗ Too many parse errors, exiting...")
                    break
                time.sleep(POLL_INTERVAL)
                continue

            # Reset error counter on successful parse
            consecutive_errors = 0

            # Check for duplicate bars
            if ts == last_ts:
                time.sleep(POLL_INTERVAL)
                continue
            last_ts = ts

            # Generate signal
            signal = make_signal(close, ema)
            
            # Display information
            status = "🔵" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"{status} [{ts}] close={close:.0f} ema={ema:.0f} atr={atr:.1f} → {signal}")

            # Write prediction - ALWAYS write file
            payload = f"{signal};{ts}\n"
            
            if write_prediction_atomic_robust(PRED, payload):
                if signal != "NONE":
                    print(f"✓ SIGNAL: {signal} for {ts}")
                else:
                    print(f"✓ No signal written for {ts}")
                
                # Pause to ensure MT5 can read
                time.sleep(COOLDOWN_SEC)
            else:
                print(f"✗ Failed to write prediction file")
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down by user request...")
            break
            
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            consecutive_errors += 1
            if consecutive_errors > max_errors:
                print("✗ Too many consecutive errors, exiting...")
                break
            time.sleep(POLL_INTERVAL)

        time.sleep(POLL_INTERVAL)

    # Cleanup on exit
    cleanup_old_predictions()
    print("✓ Cleanup completed, goodbye!")

if __name__ == "__main__":
    main()