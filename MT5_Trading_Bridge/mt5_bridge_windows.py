#!/usr/bin/env python3
"""
MT5 Trading Bridge - Windows Production Version

Optimized for Windows MetaTrader 5 environment with original paths.
Based on your code but with modern Python 3.13 features.
"""

import os
import asyncio
import time
import tempfile
import shutil
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict
import json

# ========= WINDOWS PATHS (ваши оригинальные) =========
FEAT = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\features_bt.csv"
PRED = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\prediction_bt.txt"

# ========= НАСТРОЙКИ =========
POLL_INTERVAL = 0.1        # интервал опроса
WRITE_RETRIES = 5          # количество попыток записи
COOLDOWN_SEC  = 0.5        # пауза для стабильности
EXPECTED_FIELDS = 4        # "YYYY.MM.DD HH:MM;close;ema;atr"

@dataclass
class MarketData:
    """Структура рыночных данных"""
    timestamp: str
    close: float
    ema: float
    atr: float

@dataclass
class TradingSignal:
    """Структура торгового сигнала"""
    signal: str
    timestamp: str
    confidence: float = 1.0
    metadata: Dict = None

class MT5BridgeWindows:
    """MT5 Bridge для Windows с async поддержкой"""
    
    def __init__(self):
        self.last_timestamp = None
        self.last_mtime = 0.0
        self.consecutive_errors = 0
        self.setup_logging()
        
    def setup_logging(self):
        """Настройка логирования"""
        log_dir = Path(FEAT).parent
        log_file = log_dir / "bridge.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def read_features_async(self) -> Optional[str]:
        """Асинхронное чтение последней строки"""
        if not os.path.exists(FEAT):
            return None
            
        encodings = ['ascii', 'utf-8', 'utf-16-le', 'cp1251']
        
        for attempt in range(3):
            for encoding in encodings:
                try:
                    await asyncio.sleep(0)  # Yield control
                    
                    with open(FEAT, "r", encoding=encoding, errors='ignore') as f:
                        lines = f.readlines()
                    
                    for line in reversed(lines):
                        line = line.strip().replace('\x00', '').replace('\ufeff', '')
                        if line and ';' in line and len(line.split(';')) >= EXPECTED_FIELDS:
                            self.logger.debug(f"Read success: {line[:50]}...")
                            return line
                            
                except Exception:
                    continue
            
            if attempt < 2:
                await asyncio.sleep(0.05)
        
        return None

    def parse_features(self, line: str) -> MarketData:
        """Парсинг данных из строки"""
        try:
            parts = [p.strip() for p in line.split(';')]
            if len(parts) < EXPECTED_FIELDS:
                raise ValueError(f"Expected {EXPECTED_FIELDS} fields, got {len(parts)}")

            timestamp = parts[0][:16]
            close = float(parts[-3].replace(',', '.'))
            ema = float(parts[-2].replace(',', '.'))
            atr = float(parts[-1].replace(',', '.'))

            datetime.strptime(timestamp, "%Y.%m.%d %H:%M")
            
            if close <= 0 or ema <= 0 or atr < 0:
                raise ValueError("Invalid price values")
                
            return MarketData(timestamp, close, ema, atr)
            
        except Exception as e:
            self.logger.error(f"Parse error: {e}")
            raise

    def generate_signal(self, data: MarketData) -> TradingSignal:
        """Генерация торгового сигнала"""
        try:
            if abs(data.close - data.ema) < 0.01:
                signal = "NONE"
                confidence = 0.0
            elif data.close > data.ema * 1.001:
                signal = "BUY"
                confidence = min(1.0, (data.close / data.ema - 1) * 100)
            elif data.close < data.ema * 0.999:
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
        """Асинхронная запись предсказания"""
        # Простой формат для MT5
        simple_payload = f"{signal.signal};{signal.timestamp}\n"
        
        # JSON формат для анализа
        json_payload = json.dumps({
            "signal": signal.signal,
            "timestamp": signal.timestamp,
            "confidence": signal.confidence,
            "metadata": signal.metadata or {}
        }, indent=2, ensure_ascii=False)
        
        # Записываем оба формата
        success1 = await self._write_file_atomic(PRED, simple_payload)
        
        json_path = PRED.replace('.txt', '.json')
        success2 = await self._write_file_atomic(json_path, json_payload)
        
        return success1

    async def _write_file_atomic(self, path: str, payload: str) -> bool:
        """Атомарная запись файла"""
        dir_path = os.path.dirname(path)
        
        for attempt in range(1, WRITE_RETRIES + 1):
            temp_file = None
            try:
                # Удаляем существующий файл
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        await asyncio.sleep(0.05)
                    except (PermissionError, FileNotFoundError):
                        pass
                
                # Создаем временный файл
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
                
                await asyncio.sleep(0.1)
                
                # Атомарное перемещение
                shutil.move(temp_path, path)
                
                # Проверка записи
                if os.path.exists(path):
                    with open(path, 'r', encoding='ascii') as f:
                        written = f.read().strip()
                    if written == payload.strip():
                        self.logger.debug(f"Write successful on attempt {attempt}")
                        return True
                        
            except Exception as e:
                self.logger.warning(f"Write attempt {attempt} failed: {e}")
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.remove(temp_file.name)
                    except:
                        pass
            
            if attempt < WRITE_RETRIES:
                await asyncio.sleep(0.2 * attempt)
        
        self.logger.error(f"All {WRITE_RETRIES} write attempts failed")
        return False

    async def run_forever(self):
        """Главный async цикл"""
        self.logger.info("=" * 70)
        self.logger.info("Python ML Bridge - WINDOWS ASYNC VERSION")
        self.logger.info("=" * 70)
        self.logger.info(f"Features  : {FEAT}")
        self.logger.info(f"Prediction: {PRED}")
        self.logger.info(f"Poll      : {POLL_INTERVAL}s")
        self.logger.info("✓ Starting main async loop...")
        
        try:
            while True:
                await self.process_tick()
                await asyncio.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Shutting down by user request...")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            self.logger.info("✓ Cleanup completed, goodbye!")

    async def process_tick(self):
        """Обработка одного тика"""
        try:
            if not os.path.exists(FEAT):
                return
                
            mtime = os.path.getmtime(FEAT)
            if mtime == self.last_mtime:
                return
            self.last_mtime = mtime

            line = await self.read_features_async()
            if not line:
                return

            data = self.parse_features(line)
            
            if data.timestamp == self.last_timestamp:
                return
            self.last_timestamp = data.timestamp

            signal = self.generate_signal(data)
            
            # Вывод статуса
            status_emoji = {"BUY": "🔵", "SELL": "🔴", "NONE": "⚪"}.get(signal.signal, "❓")
            self.logger.info(
                f"{status_emoji} [{data.timestamp}] "
                f"close={data.close:.0f} ema={data.ema:.0f} atr={data.atr:.1f} "
                f"→ {signal.signal} (conf: {signal.confidence:.2f})"
            )

            if await self.write_prediction_async(signal):
                if signal.signal != "NONE":
                    self.logger.info(f"✓ SIGNAL: {signal.signal} for {data.timestamp}")
                await asyncio.sleep(COOLDOWN_SEC)
            
            self.consecutive_errors = 0
            
        except Exception as e:
            self.consecutive_errors += 1
            self.logger.error(f"Tick processing error: {e}")
            
            if self.consecutive_errors > 10:
                self.logger.critical("Too many errors, shutting down...")
                raise

async def main():
    """Главная функция"""
    bridge = MT5BridgeWindows()
    await bridge.run_forever()

def run_sync():
    """Синхронная обертка"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bridge stopped")

if __name__ == "__main__":
    import sys
    print(f"✓ Running with Python {sys.version_info.major}.{sys.version_info.minor}")
    run_sync()