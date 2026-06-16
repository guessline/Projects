#!/usr/bin/env python3
"""
Simulate trading data updates to test ML Bridge signal generation
"""
import os
import time
import random
from datetime import datetime

FEATURES_FILE = "/workspace/mt_files/features_bt.csv"

def generate_trading_data(trend="up"):
    """Generate realistic trading data with trend"""
    
    # Starting values
    base_price = 1.1000
    ema = 1.0995
    
    print("Starting trading simulation...")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    for i in range(100):
        # Generate timestamp
        dt = datetime.now().strftime("%Y.%m.%d %H:%M")
        
        # Simulate price movement
        if trend == "up":
            # Uptrend - price above EMA
            close = base_price + (i * 0.0002) + random.uniform(0, 0.0005)
            ema = base_price + (i * 0.0001) + random.uniform(0, 0.0002)
        elif trend == "down":
            # Downtrend - price below EMA  
            close = base_price - (i * 0.0002) - random.uniform(0, 0.0005)
            ema = base_price - (i * 0.0001) - random.uniform(0, 0.0002)
        else:
            # Sideways - price oscillates around EMA
            close = base_price + random.uniform(-0.0010, 0.0010)
            ema = base_price + random.uniform(-0.0005, 0.0005)
        
        # ATR calculation (simplified)
        atr = abs(close - ema) * 0.5 + 0.0010
        
        # Format data line
        data_line = f"{dt};{close:.5f};{ema:.5f};{atr:.5f}"
        
        # Append to file
        with open(FEATURES_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{data_line}")
        
        # Determine expected signal
        if close > ema * 1.001:
            expected = "BUY"
            symbol = "🔵"
        elif close < ema * 0.999:
            expected = "SELL"
            symbol = "🔴"
        else:
            expected = "NONE"
            symbol = "⚪"
        
        print(f"{symbol} [{dt}] Close={close:.5f} EMA={ema:.5f} ATR={atr:.5f} -> Expected: {expected}")
        
        # Wait before next update
        time.sleep(2)

if __name__ == "__main__":
    import sys
    
    print("Trading Data Simulator")
    print("=" * 50)
    print("Usage: python3 simulate_trading.py [trend]")
    print("Trends: up, down, sideways")
    print("=" * 50)
    
    trend = sys.argv[1] if len(sys.argv) > 1 else "up"
    
    if trend not in ["up", "down", "sideways"]:
        print(f"Invalid trend: {trend}")
        print("Using default: up")
        trend = "up"
    
    print(f"Simulating {trend.upper()} trend")
    print("")
    
    try:
        generate_trading_data(trend)
    except KeyboardInterrupt:
        print("\n\nSimulation stopped by user")
        print("=" * 50)