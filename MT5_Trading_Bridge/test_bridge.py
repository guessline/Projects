#!/usr/bin/env python3
"""
Test script for MT5 Trading Bridge

This script tests the basic functionality of the bridge without requiring MT5.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add the current directory to Python path to import the bridge
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_parse_features():
    """Test the feature parsing function"""
    from mt5_bridge import parse_features_robust
    
    print("Testing feature parsing...")
    
    # Test valid data
    test_line = "2024.01.15 09:30;1.0950;1.0945;0.0015"
    try:
        ts, close, ema, atr = parse_features_robust(test_line)
        print(f"✓ Parsed: {ts}, close={close}, ema={ema}, atr={atr}")
        assert ts == "2024.01.15 09:30"
        assert close == 1.0950
        assert ema == 1.0945
        assert atr == 0.0015
        print("✓ Feature parsing test passed")
    except Exception as e:
        print(f"✗ Feature parsing test failed: {e}")
        return False
    
    # Test invalid data
    try:
        parse_features_robust("invalid;data")
        print("✗ Should have failed on invalid data")
        return False
    except:
        print("✓ Correctly rejected invalid data")
    
    return True

def test_signal_generation():
    """Test signal generation logic"""
    from mt5_bridge import make_signal
    
    print("\nTesting signal generation...")
    
    # Test BUY signal (need larger difference to trigger: > 0.01 and > ema * 1.001)
    signal = make_signal(1.100, 1.080)  # close significantly > ema
    print(f"✓ BUY test: close=1.100, ema=1.080 → {signal}")
    assert signal == "BUY"
    
    # Test SELL signal (need larger difference: > 0.01 and < ema * 0.999)
    signal = make_signal(1.080, 1.100)  # close significantly < ema
    print(f"✓ SELL test: close=1.080, ema=1.100 → {signal}")
    assert signal == "SELL"
    
    # Test NONE signal (too close)
    signal = make_signal(1.0950, 1.0950)  # close ≈ ema
    print(f"✓ NONE test: close=1.0950, ema=1.0950 → {signal}")
    assert signal == "NONE"
    
    print("✓ Signal generation tests passed")
    return True

def test_file_operations():
    """Test file reading and writing operations"""
    from mt5_bridge import _read_last_line_robust, write_prediction_atomic_robust
    
    print("\nTesting file operations...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test file writing
        test_file = os.path.join(temp_dir, "test_pred.txt")
        payload = "BUY;2024.01.15 09:30\n"
        
        if write_prediction_atomic_robust(test_file, payload):
            print("✓ File writing test passed")
        else:
            print("✗ File writing test failed")
            return False
        
        # Test file reading
        # Create test features file
        features_file = os.path.join(temp_dir, "test_features.csv")
        with open(features_file, 'w') as f:
            f.write("2024.01.15 09:30;1.0950;1.0945;0.0015\n")
            f.write("2024.01.15 09:31;1.0955;1.0947;0.0016\n")
        
        last_line = _read_last_line_robust(features_file)
        if last_line and "09:31" in last_line:
            print("✓ File reading test passed")
        else:
            print("✗ File reading test failed")
            return False
    
    return True

def create_test_data():
    """Create test data files for manual testing"""
    print("\nCreating test data files...")
    
    # Create data directory
    data_dir = Path.home() / "mt5_data"
    data_dir.mkdir(exist_ok=True)
    
    # Create features file with sample data
    features_file = data_dir / "features_bt.csv"
    sample_data = """2024.01.15 09:30;1.0950;1.0945;0.0015
2024.01.15 09:31;1.0955;1.0947;0.0016
2024.01.15 09:32;1.0960;1.0949;0.0017
2024.01.15 09:33;1.0952;1.0950;0.0015
2024.01.15 09:34;1.0958;1.0951;0.0016
"""
    
    with open(features_file, 'w') as f:
        f.write(sample_data)
    
    print(f"✓ Created test features file: {features_file}")
    print(f"✓ Data directory: {data_dir}")
    
    return str(features_file), str(data_dir / "prediction_bt.txt")

def test_full_integration():
    """Test the full integration with sample data"""
    print("\nTesting full integration...")
    
    # Import bridge components
    try:
        from mt5_bridge import parse_features_robust, make_signal, write_prediction_atomic_robust
        print("✓ Successfully imported bridge components")
    except Exception as e:
        print(f"✗ Failed to import bridge: {e}")
        return False
    
    # Create test data
    features_file, pred_file = create_test_data()
    
    # Read and process sample data
    try:
        with open(features_file, 'r') as f:
            lines = f.readlines()
        
        last_line = lines[-1].strip()
        ts, close, ema, atr = parse_features_robust(last_line)
        signal = make_signal(close, ema)
        
        payload = f"{signal};{ts}\n"
        success = write_prediction_atomic_robust(pred_file, payload)
        
        if success:
            print(f"✓ Full integration test passed")
            print(f"  Input: {last_line}")
            print(f"  Output: {payload.strip()}")
            print(f"  Prediction file: {pred_file}")
            return True
        else:
            print("✗ Failed to write prediction file")
            return False
            
    except Exception as e:
        print(f"✗ Full integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MT5 Trading Bridge - Test Suite")
    print("=" * 60)
    
    tests = [
        test_parse_features,
        test_signal_generation, 
        test_file_operations,
        test_full_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"✗ {test_func.__name__} failed")
        except Exception as e:
            print(f"✗ {test_func.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The bridge is ready to use.")
        print("\nTo run the bridge:")
        print("  python3 mt5_bridge.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()