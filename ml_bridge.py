import os
import time
import tempfile
import shutil
from datetime import datetime

# ========= ПУТИ (точно Common\Files) =========
FEAT = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\features_bt.csv"
PRED = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\prediction_bt.txt"

# ========= НАСТРОЙКИ =========
POLL_INTERVAL = 0.1        # увеличен интервал опроса
WRITE_RETRIES = 5          # увеличено количество попыток
COOLDOWN_SEC  = 0.5        # увеличена пауза для стабильности
EXPECTED_FIELDS = 4        # "YYYY.MM.DD HH:MM;close;ema;atr"

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

def make_signal(close, ema):
    """Простая логика сигналов с дополнительными проверками"""
    try:
        if abs(close - ema) < 0.01:  # слишком близко - нет сигнала
            return "NONE"
            
        if close > ema * 1.001:  # минимальный порог для BUY
            return "BUY"
        elif close < ema * 0.999:  # минимальный порог для SELL
            return "SELL"
            
        return "NONE"
    except:
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
    print("=" * 70)
    print("Python ML Bridge - FINAL ROBUST VERSION")
    print("=" * 70)
    print(f"Features  : {FEAT}")
    print(f"Prediction: {PRED}")
    print(f"Poll      : {POLL_INTERVAL}s")
    print(f"Cooldown  : {COOLDOWN_SEC}s")
    print(f"Retries   : {WRITE_RETRIES}")
    
    # Проверяем доступность директорий
    feat_dir = os.path.dirname(FEAT)
    pred_dir = os.path.dirname(PRED)
    
    if not os.path.exists(feat_dir):
        print(f"✗ CRITICAL: Features directory not found: {feat_dir}")
        return
        
    if not os.path.exists(pred_dir):
        print(f"✗ CRITICAL: Predictions directory not found: {pred_dir}")
        return
        
    if not os.access(pred_dir, os.W_OK):
        print(f"✗ CRITICAL: No write access to: {pred_dir}")
        return
    
    # Очистка старых временных файлов
    cleanup_old_predictions()
    
    print("✓ All checks passed, starting main loop...")
    print("=" * 70)

    last_ts = None
    last_mtime = 0.0
    consecutive_errors = 0
    max_errors = 10

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

            # Генерация сигнала
            signal = make_signal(close, ema)
            
            # Вывод информации
            status = "🔵" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"{status} [{ts}] close={close:.0f} ema={ema:.0f} atr={atr:.1f} → {signal}")

            # Запись предсказания - ВСЕГДА записываем файл
            payload = f"{signal};{ts}\n"
            
            if write_prediction_atomic_robust(PRED, payload):
                if signal != "NONE":
                    print(f"✓ SIGNAL: {signal} for {ts}")
                else:
                    print(f"✓ No signal written for {ts}")
                
                # Пауза для обеспечения чтения MT5
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

    # Очистка при выходе
    cleanup_old_predictions()
    print("✓ Cleanup completed, goodbye!")

if __name__ == "__main__":
    main()