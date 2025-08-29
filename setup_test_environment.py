#!/usr/bin/env python3
"""
Setup script to create test environment for ML Bridge
"""
import os
import time
from datetime import datetime

# Create test directories
mt_files_dir = "/workspace/mt_files"
os.makedirs(mt_files_dir, exist_ok=True)

print("Test Environment Setup")
print("=" * 50)
print(f"✓ Created directory: {mt_files_dir}")

# Create sample features file
features_file = os.path.join(mt_files_dir, "features_bt.csv")

# Generate sample data with headers
sample_data = []
sample_data.append("DateTime;Close;EMA;ATR")

# Generate some sample trading data
base_price = 1.1000
ema_price = 1.0995

for i in range(5):
    dt = datetime.now().strftime("%Y.%m.%d %H:%M")
    close = base_price + (i * 0.0005)
    ema = ema_price + (i * 0.0003)
    atr = 0.0012
    
    sample_data.append(f"{dt};{close:.5f};{ema:.5f};{atr:.5f}")
    time.sleep(1)  # To get different timestamps

# Write the sample data
with open(features_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(sample_data))

print(f"✓ Created sample features file: {features_file}")
print(f"✓ Written {len(sample_data)} lines of sample data")
print("")
print("Sample data (last 3 lines):")
for line in sample_data[-3:]:
    print(f"  {line}")

print("")
print("=" * 50)
print("Setup complete!")
print("")
print("To test the ML Bridge:")
print("1. Run: python3 /workspace/ml_bridge_linux.py")
print("2. In another terminal, update the features file to trigger predictions")
print("")
print("To update features file manually:")
print(f"echo '2024.01.15 14:30;1.1050;1.1040;0.0015' >> {features_file}")