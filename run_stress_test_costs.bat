@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

echo 🛡️ CRYSTAL TANK - СТРЕСС-ТЕСТ ИЗДЕРЖЕК
echo 💸 Тестирование с ВЫСОКИМИ издержками (12 б.п.)
echo 🎯 Цель: убедиться что система остается прибыльной

set "CRYSTAL_DATA_DIR=%APPDATA%\MetaQuotes\Terminal\Common\Files"

rem === СТРЕСС-ТЕСТ: ВЫСОКИЕ ИЗДЕРЖКИ ===
set "CRYSTAL_SIGNAL_MODE=margin"
set "CRYSTAL_TH_AUTO=1"
set "CRYSTAL_TH_GRID=0.09,0.14,0.005"
set "CRYSTAL_TARGET_THRESHOLD=0.00011"
set "CRYSTAL_MIN_SIGNALS=2"
set "CRYSTAL_MIN_HOLD=3"
set "CRYSTAL_MIN_TURNOVER=0"
set "CRYSTAL_SESSION=none"

rem !!! ВЫСОКИЕ ИЗДЕРЖКИ ДЛЯ СТРЕСС-ТЕСТА !!!
set "CRYSTAL_COMMISSION=0.0008"
set "CRYSTAL_SLIPPAGE=0.0004"

rem === ДЕТЕРМИНИЗМ ===
set "PYTHONHASHSEED=0"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=UTF-8"
set "PYTHONUNBUFFERED=1"

echo 🛡️ СТРЕСС-ТЕСТ КОНФИГУРАЦИЯ:
echo    💸 Commission: %CRYSTAL_COMMISSION% (0.08%% vs 0.04%%)
echo    💸 Slippage: %CRYSTAL_SLIPPAGE% (0.04%% vs 0.01%%)
echo    💸 ИТОГО: 0.12%% издержки (vs 0.05%% базовые)
echo    📊 Увеличение издержек: +140%%

echo 🎯 КРИТЕРИИ ПРОХОЖДЕНИЯ СТРЕСС-ТЕСТА:
echo    💰 PnL: должен остаться >0 (было +0.572)
echo    📈 Sharpe: должен остаться >1.0 (было 38.9)
echo    🎯 Сигналов: должно остаться >100 (было 939)
echo    📉 Деградация: <50%% от базовых метрик

echo 🚨 ОЖИДАЕМЫЕ ИЗМЕНЕНИЯ:
echo    📉 PnL: снижение ~20-30%%
echo    📉 Sharpe: снижение ~15-25%%
echo    📉 Turnover: возможное снижение
echo    🎯 Deploy: может вырасти до ~0.11-0.12

echo 🚀 Запуск стресс-теста с высокими издержками...
echo ⏱️ Время выполнения: ~10-15 минут

if not exist "%CRYSTAL_DATA_DIR%\ml_features.csv" (
    echo ❌ Файл ml_features.csv не найден!
    echo 💡 Создайте расширенные данные: python create_extended_m5_data.py
    pause
    exit /b 1
)

python -u -X utf8 ultimate_crystal_tank_universal.py

if errorlevel 1 (
    echo ❌ Стресс-тест провален
) else (
    echo ✅ СТРЕСС-ТЕСТ ЗАВЕРШЕН!
    echo 🛡️ Проверьте устойчивость к высоким издержкам
)

echo.
echo 📊 АНАЛИЗ РЕЗУЛЬТАТОВ:
echo    ✅ Если PnL>0: система устойчива к издержкам
echo    ⚠️ Если PnL≤0: нужно снизить turnover или поднять пороги
echo    🎯 Если Deploy<0.15: готов к реальной торговле
pause