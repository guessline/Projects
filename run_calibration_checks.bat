@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

echo 🔬 CRYSTAL TANK - КАЛИБРОВКА И SANITY-ЧЕКИ
echo 🎯 Проверка качества вероятностей и устойчивости
echo 📊 ECE=0.317 требует дополнительной калибровки

set "CRYSTAL_DATA_DIR=%APPDATA%\MetaQuotes\Terminal\Common\Files"

rem === БАЗОВАЯ КОНФИГУРАЦИЯ M5 ===
set "CRYSTAL_SIGNAL_MODE=margin"
set "CRYSTAL_TH_AUTO=1"
set "CRYSTAL_TH_GRID=0.09,0.14,0.005"
set "CRYSTAL_TARGET_THRESHOLD=0.00011"
set "CRYSTAL_MIN_SIGNALS=2"
set "CRYSTAL_MIN_HOLD=3"
set "CRYSTAL_MIN_TURNOVER=0"
set "CRYSTAL_SESSION=none"
set "CRYSTAL_COMMISSION=0.0004"
set "CRYSTAL_SLIPPAGE=0.0001"

rem === ДЕТЕРМИНИЗМ ===
set "PYTHONHASHSEED=0"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=UTF-8"
set "PYTHONUNBUFFERED=1"

echo 🔬 ПЛАН КАЛИБРОВОЧНЫХ ТЕСТОВ:
echo    1️⃣ Isotonic калибровка (vs Platt sigmoid)
echo    2️⃣ Чувствительность к порогу (0.095-0.115)
echo    3️⃣ Перемешанные метки (должно развалиться)
echo    4️⃣ Анализ ECE и Brier Score

echo.
echo 📊 ТЕСТ 1: ISOTONIC КАЛИБРОВКА
echo 🎯 Цель: улучшить ECE с 0.317 до <0.1
pause

rem Временно переключаем на isotonic
set "CRYSTAL_CALIBRATION=isotonic"
echo 🚀 Запуск с isotonic калибровкой...
python -u -X utf8 ultimate_crystal_tank_universal.py > calibration_isotonic.log 2>&1

echo ✅ Isotonic тест завершен, лог: calibration_isotonic.log
echo.

echo 📊 ТЕСТ 2: ЧУВСТВИТЕЛЬНОСТЬ К ПОРОГУ
echo 🎯 Цель: проверить стабильность при ±10%% от 0.101
pause

rem Тест с низким порогом (0.095)
set "CRYSTAL_TH_GRID=0.085,0.105,0.005"
echo 🚀 Запуск с низкими порогами (0.085-0.105)...
python -u -X utf8 ultimate_crystal_tank_universal.py > threshold_low.log 2>&1

rem Тест с высоким порогом (0.115)  
set "CRYSTAL_TH_GRID=0.105,0.125,0.005"
echo 🚀 Запуск с высокими порогами (0.105-0.125)...
python -u -X utf8 ultimate_crystal_tank_universal.py > threshold_high.log 2>&1

echo ✅ Тесты чувствительности завершены
echo    📄 Логи: threshold_low.log, threshold_high.log
echo.

echo 📊 ТЕСТ 3: ПЕРЕМЕШАННЫЕ МЕТКИ (SANITY CHECK)
echo 🎯 Цель: система должна показать PnL≈0, Sharpe≈0
echo ⚠️ ВНИМАНИЕ: этот тест ДОЛЖЕН провалиться!
pause

rem Создаем версию с перемешанными метками
python -c "
import pandas as pd
import numpy as np
import os

data_dir = os.environ.get('CRYSTAL_DATA_DIR', os.path.expanduser(r'~\AppData\Roaming\MetaQuotes\Terminal\Common\Files'))
file_path = os.path.join(data_dir, 'ml_features.csv')

if os.path.exists(file_path):
    df = pd.read_csv(file_path, sep=';')
    
    # Сохраняем оригинал
    backup_path = os.path.join(data_dir, 'ml_features_original.csv')
    df.to_csv(backup_path, sep=';', index=False)
    
    # Перемешиваем target (это должно убить предиктивность!)
    np.random.seed(42)
    df['target'] = np.random.permutation(df['target'].values)
    
    # Сохраняем перемешанную версию
    shuffled_path = os.path.join(data_dir, 'ml_features.csv')
    df.to_csv(shuffled_path, sep=';', index=False)
    
    print('✅ Метки перемешаны - система должна провалиться!')
else:
    print('❌ Файл данных не найден!')
"

echo 🚀 Запуск с перемешанными метками...
python -u -X utf8 ultimate_crystal_tank_universal.py > shuffled_labels.log 2>&1

echo ✅ Sanity-check завершен, лог: shuffled_labels.log

rem Восстанавливаем оригинальные данные
python -c "
import pandas as pd
import os
import shutil

data_dir = os.environ.get('CRYSTAL_DATA_DIR', os.path.expanduser(r'~\AppData\Roaming\MetaQuotes\Terminal\Common\Files'))
backup_path = os.path.join(data_dir, 'ml_features_original.csv')
original_path = os.path.join(data_dir, 'ml_features.csv')

if os.path.exists(backup_path):
    shutil.move(backup_path, original_path)
    print('✅ Оригинальные данные восстановлены')
else:
    print('❌ Бэкап не найден!')
"

echo.
echo 🔬 ВСЕ КАЛИБРОВОЧНЫЕ ТЕСТЫ ЗАВЕРШЕНЫ!
echo.
echo 📊 АНАЛИЗ РЕЗУЛЬТАТОВ:
echo    📄 calibration_isotonic.log - isotonic vs sigmoid
echo    📄 threshold_low.log - низкие пороги  
echo    📄 threshold_high.log - высокие пороги
echo    📄 shuffled_labels.log - перемешанные метки (должен быть плохим!)
echo.
echo 🎯 КРИТЕРИИ ПРОХОЖДЕНИЯ:
echo    ✅ Isotonic: ECE < 0.1, Brier улучшен
echo    ✅ Пороги: PnL стабилен ±20%% при ±10%% порогов
echo    ✅ Shuffle: PnL≈0, Sharpe≈0 (система честная!)
echo.
echo 🏆 Если все тесты пройдены - система готова к РЕАЛЬНОЙ ТОРГОВЛЕ!
pause