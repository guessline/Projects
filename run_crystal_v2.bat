@echo off
echo 🏆 ULTIMATE CRYSTAL PERFECT V2 LAUNCHER
echo 💎 Полный детерминизм (все баги исправлены)

set PYTHONHASHSEED=0
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
set OMP_NUM_THREADS=1

echo ✅ Env переменные установлены для детерминизма
echo 🚀 Запускаем ULTIMATE CRYSTAL PERFECT V2...
python ultimate_crystal_perfect_v2.py

echo.
echo 📊 Результаты:
echo 📄 Метаданные: ultimate_crystal_metadata.json
echo 🤖 Модель: ultimate_crystal_model.pkl

pause