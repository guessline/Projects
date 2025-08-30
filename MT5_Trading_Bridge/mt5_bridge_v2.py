#!/usr/bin/env python3
"""
MT5 Trading Bridge v2.0 - Latest Python Version

Enhanced bridge with modern Python features (3.11+):
- Async/await support for better performance
- Type hints for better code quality
- Dataclasses for structured data
- Context managers for resource handling
- Enhanced logging and monitoring
"""

import os
import asyncio
import time
import tempfile
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List
from contextlib import asynccontextmanager
import json

# ========= CONFIGURATION =========
@dataclass
class BridgeConfig:
    """Configuration for the MT5 Bridge"""
    features_path: Path
    predictions_path: Path
    poll_interval: float = 0.1
    write_retries: int = 5
    cooldown_sec: float = 0.5
    expected_fields: int = 4
    max_consecutive_errors: int = 10
    
    # Signal generation parameters
    min_price_diff: float = 0.01
    buy_threshold: float = 1.001
    sell_threshold: float = 0.999
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None

@dataclass
class MarketData:
    """Market data structure"""
    timestamp: str
    close: float
    ema: float
    atr: float
    
    def __post_init__(self):
        """Validate data after initialization"""
        if self.close <= 0 or self.ema <= 0 or self.atr < 0:
            raise ValueError(f"Invalid market data: close={self.close}, ema={self.ema}, atr={self.atr}")

@dataclass
class TradingSignal:
    """Trading signal structure"""
    signal: str  # BUY, SELL, NONE, CLOSE_ALL
    timestamp: str
    confidence: float = 1.0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class MT5Bridge:
    """Modern MT5 Trading Bridge with async support"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.last_timestamp = None
        self.last_mtime = 0.0
        self.consecutive_errors = 0
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        handlers = [logging.StreamHandler()]
        if self.config.log_file:
            handlers.append(logging.FileHandler(self.config.log_file))
            
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format=log_format,
            handlers=handlers
        )
        self.logger = logging.getLogger(__name__)
        
    def ensure_directories(self):
        """Ensure all required directories exist"""
        self.config.features_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.predictions_path.parent.mkdir(parents=True, exist_ok=True)
        
    async def read_features_async(self) -> Optional[str]:
        """Asynchronously read the last line from features file"""
        if not self.config.features_path.exists():
            return None
            
        encodings = ['ascii', 'utf-8', 'utf-16-le', 'utf-16', 'cp1251', 'latin-1']
        
        for attempt in range(3):
            for encoding in encodings:
                try:
                    # Use asyncio to avoid blocking
                    await asyncio.sleep(0)  # Yield control
                    
                    with open(self.config.features_path, "r", encoding=encoding, errors='ignore') as f:
                        lines = f.readlines()
                    
                    # Find last valid line
                    for line in reversed(lines):
                        line = line.strip().replace('\x00', '').replace('\ufeff', '')
                        if line and ';' in line and len(line.split(';')) >= self.config.expected_fields:
                            self.logger.debug(f"Read success with {encoding}: {line[:60]}...")
                            return line
                            
                except Exception as e:
                    self.logger.debug(f"Read attempt failed with {encoding}: {e}")
                    continue
            
            if attempt < 2:
                await asyncio.sleep(0.05)
        
        self.logger.warning("Failed to read features file after all attempts")
        return None
    
    def parse_features(self, line: str) -> MarketData:
        """Parse features line into structured data"""
        try:
            parts = [p.strip() for p in line.split(';')]
            if len(parts) < self.config.expected_fields:
                raise ValueError(f"Expected {self.config.expected_fields} fields, got {len(parts)}")

            timestamp = parts[0][:16]  # YYYY.MM.DD HH:MM
            close = float(parts[-3].replace(',', '.'))
            ema = float(parts[-2].replace(',', '.'))
            atr = float(parts[-1].replace(',', '.'))

            # Validate timestamp format
            datetime.strptime(timestamp, "%Y.%m.%d %H:%M")
            
            return MarketData(timestamp, close, ema, atr)
            
        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            self.logger.debug(f"Raw line: {repr(line[:100])}")
            raise

    def generate_signal(self, data: MarketData) -> TradingSignal:
        """Generate trading signal from market data"""
        try:
            # Check if prices are too close
            if abs(data.close - data.ema) < self.config.min_price_diff:
                signal = "NONE"
                confidence = 0.0
            elif data.close > data.ema * self.config.buy_threshold:
                signal = "BUY"
                confidence = min(1.0, (data.close / data.ema - 1) * 100)  # Confidence based on distance
            elif data.close < data.ema * self.config.sell_threshold:
                signal = "SELL"
                confidence = min(1.0, (1 - data.close / data.ema) * 100)
            else:
                signal = "NONE"
                confidence = 0.0
                
            return TradingSignal(
                signal=signal,
                timestamp=data.timestamp,
                confidence=confidence,
                metadata={
                    "close": data.close,
                    "ema": data.ema,
                    "atr": data.atr,
                    "spread_ratio": abs(data.close - data.ema) / data.ema
                }
            )
            
        except Exception as e:
            self.logger.error(f"Signal generation error: {e}")
            return TradingSignal("NONE", data.timestamp, 0.0)

    async def write_prediction_async(self, signal: TradingSignal) -> bool:
        """Asynchronously write prediction with enhanced format"""
        # Enhanced payload with metadata
        payload_dict = {
            "signal": signal.signal,
            "timestamp": signal.timestamp,
            "confidence": signal.confidence,
            "metadata": signal.metadata
        }
        
        # Simple format for MT5 compatibility
        simple_payload = f"{signal.signal};{signal.timestamp}\n"
        
        # Also write detailed JSON for advanced analysis
        json_payload = json.dumps(payload_dict, indent=2)
        json_path = self.config.predictions_path.with_suffix('.json')
        
        # Write both formats
        success1 = await self._write_file_atomic(self.config.predictions_path, simple_payload)
        success2 = await self._write_file_atomic(json_path, json_payload)
        
        return success1  # MT5 only needs the simple format

    async def _write_file_atomic(self, path: Path, payload: str) -> bool:
        """Atomic file writing with async support"""
        for attempt in range(1, self.config.write_retries + 1):
            try:
                # Remove existing file
                if path.exists():
                    try:
                        path.unlink()
                        await asyncio.sleep(0.05)
                    except (PermissionError, FileNotFoundError):
                        pass
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    encoding='ascii',
                    delete=False,
                    dir=path.parent,
                    prefix=f'{path.stem}_tmp_',
                    suffix=path.suffix
                ) as temp_file:
                    temp_file.write(payload)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                    temp_path = Path(temp_file.name)
                
                await asyncio.sleep(0.1)
                
                # Atomic move
                shutil.move(str(temp_path), str(path))
                
                # Verify write
                if path.exists() and path.read_text().strip() == payload.strip():
                    self.logger.debug(f"Write successful on attempt {attempt}")
                    return True
                    
            except Exception as e:
                self.logger.warning(f"Write attempt {attempt} failed: {e}")
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
            
            if attempt < self.config.write_retries:
                await asyncio.sleep(0.2 * attempt)
        
        self.logger.error(f"All {self.config.write_retries} write attempts failed")
        return False

    async def cleanup_temp_files(self):
        """Cleanup temporary files"""
        try:
            pred_dir = self.config.predictions_path.parent
            for file_path in pred_dir.glob('*_tmp_*'):
                try:
                    file_path.unlink()
                except:
                    pass
        except Exception as e:
            self.logger.debug(f"Cleanup error: {e}")

    async def run_forever(self):
        """Main async loop"""
        self.logger.info("=" * 70)
        self.logger.info("Python ML Bridge v2.0 - ASYNC VERSION")
        self.logger.info("=" * 70)
        self.logger.info(f"Features  : {self.config.features_path}")
        self.logger.info(f"Prediction: {self.config.predictions_path}")
        self.logger.info(f"Poll      : {self.config.poll_interval}s")
        
        self.ensure_directories()
        await self.cleanup_temp_files()
        
        self.logger.info("✓ Starting main async loop...")
        
        try:
            while True:
                await self.process_tick()
                await asyncio.sleep(self.config.poll_interval)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Shutting down by user request...")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            await self.cleanup_temp_files()
            self.logger.info("✓ Cleanup completed, goodbye!")

    async def process_tick(self):
        """Process one tick of data"""
        try:
            # Check file modification
            if not self.config.features_path.exists():
                return
                
            mtime = self.config.features_path.stat().st_mtime
            if mtime == self.last_mtime:
                return
            self.last_mtime = mtime

            # Read and parse features
            line = await self.read_features_async()
            if not line:
                return

            data = self.parse_features(line)
            
            # Skip duplicate timestamps
            if data.timestamp == self.last_timestamp:
                return
            self.last_timestamp = data.timestamp

            # Generate signal
            signal = self.generate_signal(data)
            
            # Display status
            status_emoji = {"BUY": "🔵", "SELL": "🔴", "NONE": "⚪"}.get(signal.signal, "❓")
            self.logger.info(
                f"{status_emoji} [{data.timestamp}] "
                f"close={data.close:.0f} ema={data.ema:.0f} atr={data.atr:.1f} "
                f"→ {signal.signal} (conf: {signal.confidence:.2f})"
            )

            # Write prediction
            if await self.write_prediction_async(signal):
                if signal.signal != "NONE":
                    self.logger.info(f"✓ SIGNAL: {signal.signal} for {data.timestamp}")
                await asyncio.sleep(self.config.cooldown_sec)
            
            # Reset error counter on success
            self.consecutive_errors = 0
            
        except Exception as e:
            self.consecutive_errors += 1
            self.logger.error(f"Tick processing error: {e}")
            
            if self.consecutive_errors > self.config.max_consecutive_errors:
                self.logger.critical("Too many consecutive errors, shutting down...")
                raise

def create_default_config() -> BridgeConfig:
    """Create default configuration"""
    data_dir = Path.home() / "mt5_data"
    
    return BridgeConfig(
        features_path=data_dir / "features_bt.csv",
        predictions_path=data_dir / "prediction_bt.txt",
        log_file=data_dir / "bridge.log"
    )

def create_sample_data(config: BridgeConfig):
    """Create sample data for testing"""
    sample_data = """2024.12.01 09:30;1.0950;1.0945;0.0015
2024.12.01 09:31;1.0955;1.0947;0.0016
2024.12.01 09:32;1.0960;1.0949;0.0017
2024.12.01 09:33;1.0952;1.0950;0.0015
2024.12.01 09:34;1.0958;1.0951;0.0016
"""
    
    if not config.features_path.exists():
        print(f"Creating sample features file at: {config.features_path}")
        config.features_path.parent.mkdir(parents=True, exist_ok=True)
        config.features_path.write_text(sample_data)

async def main():
    """Main async entry point"""
    # Load configuration
    config = create_default_config()
    
    # Override with environment variables
    if os.getenv("MT5_FEATURES_PATH"):
        config.features_path = Path(os.getenv("MT5_FEATURES_PATH"))
    if os.getenv("MT5_PREDICTION_PATH"):
        config.predictions_path = Path(os.getenv("MT5_PREDICTION_PATH"))
    
    # Create sample data if needed
    create_sample_data(config)
    
    # Create and run bridge
    bridge = MT5Bridge(config)
    await bridge.run_forever()

def run_sync():
    """Synchronous wrapper for backwards compatibility"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bridge stopped by user")
    except Exception as e:
        print(f"✗ Bridge crashed: {e}")

if __name__ == "__main__":
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        print("⚠️  Warning: Python 3.8+ recommended for full async support")
        print("Current version:", sys.version)
        print("Falling back to synchronous mode...")
        
        # Import and run the original bridge
        from mt5_bridge import main as main_sync
        main_sync()
    else:
        print(f"✓ Running with Python {sys.version_info.major}.{sys.version_info.minor}")
        run_sync()