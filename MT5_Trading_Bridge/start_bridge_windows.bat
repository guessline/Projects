@echo off
REM MT5 Trading Bridge - Windows Launcher
REM Запуск Python моста на Windows с MT5

echo ========================================
echo MT5 Trading Bridge - Windows Version
echo ========================================

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен!
    echo Скачайте с https://python.org
    pause
    exit /b 1
)

REM Переход в папку MT5 Files
cd /d "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files"

REM Создание папки для Python если не существует
if not exist "python_bridge" mkdir python_bridge
cd python_bridge

REM Проверка файлов
if not exist "mt5_bridge_windows.py" (
    echo ОШИБКА: Файл mt5_bridge_windows.py не найден!
    echo Скопируйте файлы в папку: %CD%
    pause
    exit /b 1
)

REM Установка переменных среды
set MT5_FEATURES_PATH=C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\features_bt.csv
set MT5_PREDICTION_PATH=C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\prediction_bt.txt

echo Папка данных: %CD%
echo Файл признаков: %MT5_FEATURES_PATH%
echo Файл предсказаний: %MT5_PREDICTION_PATH%
echo ========================================

REM Запуск моста
echo Запуск Python моста...
echo Нажмите Ctrl+C для остановки
echo ========================================

python mt5_bridge_windows.py

echo ========================================
echo Мост остановлен
pause