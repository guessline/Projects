import os
import time
import tempfile
import shutil
import json
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

# ========= ПУТИ (точно Common\Files) =========
FEAT = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\features_bt.csv"
PRED = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\prediction_bt.txt"

# ========= НАСТРОЙКИ =========
POLL_INTERVAL = 0.1        # увеличен интервал опроса
WRITE_RETRIES = 5          # увеличено количество попыток
COOLDOWN_SEC  = 0.5        # увеличена пауза для стабильности
EXPECTED_FIELDS = 4        # "YYYY.MM.DD HH:MM;close;ema;atr"

# ========= НАСТРОЙКИ ЛОГИРОВАНИЯ =========
LOG_FILE = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ml_bridge.log"
STATS_FILE = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ml_bridge_stats.json"

# ========= НАСТРОЙКИ СИГНАЛОВ =========
SIGNAL_THRESHOLD_BUY = 1.001   # минимальный порог для BUY сигнала
SIGNAL_THRESHOLD_SELL = 0.999  # минимальный порог для SELL сигнала
MIN_PRICE_DIFF = 0.01          # минимальная разница цены для сигнала

# ========= НАСТРОЙКА ЛОГИРОВАНИЯ =========
def setup_logging():
    """Настройка системы логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# ========= СТАТИСТИКА =========
class MLBridgeStats:
    """Класс для сбора статистики работы ML Bridge"""
    
    def __init__(self):
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'none_signals': 0,
            'read_errors': 0,
            'write_errors': 0,
            'parse_errors': 0,
            'last_signal_time': None,
            'last_signal_type': None,
            'uptime_hours': 0
        }
    
    def update_signal(self, signal_type: str):
        """Обновление статистики сигнала"""
        self.stats['total_signals'] += 1
        self.stats['last_signal_time'] = datetime.now().isoformat()
        self.stats['last_signal_type'] = signal_type
        
        if signal_type == 'BUY':
            self.stats['buy_signals'] += 1
        elif signal_type == 'SELL':
            self.stats['sell_signals'] += 1
        else:
            self.stats['none_signals'] += 1
    
    def update_error(self, error_type: str):
        """Обновление статистики ошибок"""
        if error_type == 'read':
            self.stats['read_errors'] += 1
        elif error_type == 'write':
            self.stats['write_errors'] += 1
        elif error_type == 'parse':
            self.stats['parse_errors'] += 1
    
    def save_stats(self):
        """Сохранение статистики в файл"""
        try:
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"✗ Failed to save stats: {e}")
    
    def load_stats(self):
        """Загрузка статистики из файла"""
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    self.stats.update(json.load(f))
        except Exception as e:
            print(f"✗ Failed to load stats: {e}")
    
    def print_stats(self):
        """Вывод текущей статистики"""
        print("\n" + "=" * 50)
        print("CURRENT STATISTICS")
        print("=" * 50)
        print(f"Total signals: {self.stats['total_signals']}")
        print(f"BUY: {self.stats['buy_signals']} | SELL: {self.stats['sell_signals']} | NONE: {self.stats['none_signals']}")
        print(f"Errors - Read: {self.stats['read_errors']}, Write: {self.stats['write_errors']}, Parse: {self.stats['parse_errors']}")
        print(f"Last signal: {self.stats['last_signal_type']} at {self.stats['last_signal_time']}")
        print("=" * 50)

def _read_last_line_robust(path):
    """
    Надежное чтение последней строки файла с множественными попытками
    """
    if not os.path.exists(path):
        return None
        
    # Попытки чтения с разными кодировками
    encodings_to_try = ['ascii', 'utf-8', 'utf-16-le', 'utf-16', 'cp1251', 'latin-1']
    
    for attempt in range(3):  # 3 попытки чтения
        for encoding in encodings_to_try:
            try:
                with open(path, "r", encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()
                
                # Ищем последнюю валидную строку
                for line in reversed(lines):
                    line = line.strip().replace('\x00', '').replace('\ufeff', '')
                    if line and ';' in line and len(line.split(';')) >= EXPECTED_FIELDS:
                        print(f"✓ Read success with {encoding}: {line[:60]}...")
                        return line
                        
            except Exception as e:
                continue
        
        if attempt < 2:
            time.sleep(0.05)  # короткая пауза между попытками
    
    print("✗ Failed to read file after all attempts")
    return None

def parse_features_robust(line):
    """Надежный парсинг с проверками"""
    try:
        parts = [p.strip() for p in line.split(';')]
        if len(parts) < EXPECTED_FIELDS:
            raise ValueError(f"Expected {EXPECTED_FIELDS} fields, got {len(parts)}")

        ts = parts[0][:16]  # строго до минут
        
        # Парсинг чисел с заменой запятых на точки
        close = float(parts[-3].replace(',', '.'))
        ema   = float(parts[-2].replace(',', '.'))
        atr   = float(parts[-1].replace(',', '.'))

        # Валидация временной метки
        datetime.strptime(ts, "%Y.%m.%d %H:%M")
        
        # Проверка разумности значений
        if close <= 0 or ema <= 0 or atr < 0:
            raise ValueError("Invalid price values")
            
        return ts, close, ema, atr
        
    except Exception as e:
        print(f"✗ Parse error: {e}")
        print(f"Raw line: {repr(line[:100])}")
        raise

def make_signal(close: float, ema: float, atr: float = None) -> str:
    """
    Улучшенная логика генерации сигналов с учетом ATR
    
    Args:
        close: Текущая цена закрытия
        ema: Значение экспоненциальной скользящей средней
        atr: Значение Average True Range (опционально)
    
    Returns:
        str: 'BUY', 'SELL' или 'NONE'
    """
    try:
        # Проверка на минимальную разницу
        if abs(close - ema) < MIN_PRICE_DIFF:
            return "NONE"
        
        # Расчет относительной разности
        price_ratio = close / ema
        
        # Простая логика без ATR
        if atr is None:
            if price_ratio > SIGNAL_THRESHOLD_BUY:
                return "BUY"
            elif price_ratio < SIGNAL_THRESHOLD_SELL:
                return "SELL"
            return "NONE"
        
        # Улучшенная логика с учетом ATR
        atr_threshold = atr / ema if ema > 0 else 0.001
        
        # Динамические пороги на основе волатильности
        buy_threshold = 1.0 + max(atr_threshold * 0.5, 0.001)
        sell_threshold = 1.0 - max(atr_threshold * 0.5, 0.001)
        
        if price_ratio > buy_threshold:
            return "BUY"
        elif price_ratio < sell_threshold:
            return "SELL"
        
        return "NONE"
        
    except Exception as e:
        print(f"✗ Signal generation error: {e}")
        return "NONE"

def write_prediction_atomic_robust(path, payload):
    """
    Максимально надежная запись через временный файл с обходом блокировки
    """
    dir_path = os.path.dirname(path)
    
    for attempt in range(1, WRITE_RETRIES + 1):
        temp_file = None
        try:
            # Удаляем существующий файл перед записью нового
            if os.path.exists(path):
                try:
                    os.remove(path)
                    time.sleep(0.05)  # Пауза для освобождения файла MT5
                except (PermissionError, FileNotFoundError):
                    # Файл может быть заблокирован MT5, попробуем другой подход
                    pass
            
            # Создаем временный файл в той же директории
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
            
            # Даем MT5 время освободить старый файл
            time.sleep(0.1)
            
            # Пытаемся атомарно переместить файл
            try:
                shutil.move(temp_path, path)
            except PermissionError:
                # Если MT5 все еще держит файл, ждем и пробуем еще раз
                time.sleep(0.2)
                if os.path.exists(path):
                    os.remove(path)
                time.sleep(0.1)
                shutil.move(temp_path, path)
            
            # Проверяем что файл записался корректно
            if os.path.exists(path):
                with open(path, 'r', encoding='ascii') as f:
                    written_content = f.read().strip()
                if written_content == payload.strip():
                    print(f"✓ Write successful on attempt {attempt}")
                    return True
                    
        except PermissionError as e:
            print(f"✗ Write attempt {attempt} - Permission denied (MT5 file lock)")
            # Очистка временного файла
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except:
                    pass
                    
        except Exception as e:
            print(f"✗ Write attempt {attempt} failed: {e}")
            # Очистка временного файла при ошибке
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except:
                    pass
        
        if attempt < WRITE_RETRIES:
            time.sleep(0.2 * attempt)  # Увеличивающаяся пауза
    
    print(f"✗ All {WRITE_RETRIES} write attempts failed")
    return False

def cleanup_old_predictions():
    """Очистка старых файлов предсказаний"""
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

def main():
    # Настройка логирования
    logger = setup_logging()
    
    # Инициализация статистики
    stats = MLBridgeStats()
    stats.load_stats()
    
    print("=" * 70)
    print("Python ML Bridge - ENHANCED VERSION")
    print("=" * 70)
    print(f"Features  : {FEAT}")
    print(f"Prediction: {PRED}")
    print(f"Poll      : {POLL_INTERVAL}s")
    print(f"Cooldown  : {COOLDOWN_SEC}s")
    print(f"Retries   : {WRITE_RETRIES}")
    print(f"Log File  : {LOG_FILE}")
    print(f"Stats File: {STATS_FILE}")
    
    logger.info("ML Bridge starting up...")
    
    # Проверяем доступность директорий
    feat_dir = os.path.dirname(FEAT)
    pred_dir = os.path.dirname(PRED)
    
    if not os.path.exists(feat_dir):
        error_msg = f"Features directory not found: {feat_dir}"
        print(f"✗ CRITICAL: {error_msg}")
        logger.error(error_msg)
        return
        
    if not os.path.exists(pred_dir):
        error_msg = f"Predictions directory not found: {pred_dir}"
        print(f"✗ CRITICAL: {error_msg}")
        logger.error(error_msg)
        return
        
    if not os.access(pred_dir, os.W_OK):
        error_msg = f"No write access to: {pred_dir}"
        print(f"✗ CRITICAL: {error_msg}")
        logger.error(error_msg)
        return
    
    # Очистка старых временных файлов
    cleanup_old_predictions()
    
    logger.info("All checks passed, starting main loop...")
    print("✓ All checks passed, starting main loop...")
    print("=" * 70)

    last_ts = None
    last_mtime = 0.0
    consecutive_errors = 0
    max_errors = 10
    stats_counter = 0  # Счетчик для периодического вывода статистики

    while True:
        try:
            # Проверка существования файла признаков
            if not os.path.exists(FEAT):
                if consecutive_errors == 0:
                    print("⏳ Waiting for features file...")
                time.sleep(POLL_INTERVAL)
                continue

            # Проверка изменения файла
            try:
                mtime = os.path.getmtime(FEAT)
            except OSError:
                time.sleep(POLL_INTERVAL)
                continue
                
            if mtime == last_mtime:
                time.sleep(POLL_INTERVAL)
                continue
                
            last_mtime = mtime

            # Чтение файла признаков
            line = _read_last_line_robust(FEAT)
            if not line:
                print("⏳ No valid data in features file")
                time.sleep(POLL_INTERVAL)
                continue

            # Парсинг данных
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

            # Сброс счетчика ошибок при успешном парсинге
            consecutive_errors = 0

            # Проверка дублирования баров
            if ts == last_ts:
                time.sleep(POLL_INTERVAL)
                continue
            last_ts = ts
            
            # Периодический вывод статистики (каждые 100 итераций)
            stats_counter += 1
            if stats_counter % 100 == 0:
                stats.print_stats()
                stats.save_stats()  # Сохраняем статистику периодически

            # Генерация сигнала с учетом ATR
            signal = make_signal(close, ema, atr)
            
            # Обновление статистики
            stats.update_signal(signal)
            
            # Вывод информации
            status = "🔵" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"{status} [{ts}] close={close:.0f} ema={ema:.0f} atr={atr:.1f} → {signal}")
            
            # Логирование сигнала
            logger.info(f"Signal generated: {signal} at {ts} - close={close:.0f}, ema={ema:.0f}, atr={atr:.1f}")

            # Запись предсказания - ВСЕГДА записываем файл
            payload = f"{signal};{ts}\n"
            
            if write_prediction_atomic_robust(PRED, payload):
                if signal != "NONE":
                    print(f"✓ SIGNAL: {signal} for {ts}")
                    logger.info(f"Signal written successfully: {signal} for {ts}")
                else:
                    print(f"✓ No signal written for {ts}")
                
                # Пауза для обеспечения чтения MT5
                time.sleep(COOLDOWN_SEC)
            else:
                error_msg = f"Failed to write prediction file"
                print(f"✗ {error_msg}")
                logger.error(error_msg)
                stats.update_error('write')
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down by user request...")
            logger.info("ML Bridge shutting down by user request")
            break
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"✗ {error_msg}")
            logger.error(error_msg, exc_info=True)
            stats.update_error('parse')
            consecutive_errors += 1
            if consecutive_errors > max_errors:
                print("✗ Too many consecutive errors, exiting...")
                logger.error("Too many consecutive errors, exiting...")
                break
            time.sleep(POLL_INTERVAL)

        time.sleep(POLL_INTERVAL)

    # Сохранение статистики и очистка при выходе
    stats.save_stats()
    cleanup_old_predictions()
    
    # Вывод итоговой статистики
    print("\n" + "=" * 70)
    print("ML BRIDGE STATISTICS")
    print("=" * 70)
    print(f"Total signals generated: {stats.stats['total_signals']}")
    print(f"BUY signals: {stats.stats['buy_signals']}")
    print(f"SELL signals: {stats.stats['sell_signals']}")
    print(f"NONE signals: {stats.stats['none_signals']}")
    print(f"Read errors: {stats.stats['read_errors']}")
    print(f"Write errors: {stats.stats['write_errors']}")
    print(f"Parse errors: {stats.stats['parse_errors']}")
    print(f"Last signal: {stats.stats['last_signal_type']} at {stats.stats['last_signal_time']}")
    print("=" * 70)
    
    logger.info("ML Bridge shutdown completed")
    print("✓ Cleanup completed, goodbye!")

if __name__ == "__main__":
    main()