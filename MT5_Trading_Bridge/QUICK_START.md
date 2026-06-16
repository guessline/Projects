# ⚡ **БЫСТРЫЙ СТАРТ - ГДЕ ЗАПУСКАТЬ**

## 🎯 **МОЯ РЕКОМЕНДАЦИЯ: Windows ПК с MT5**

### 📍 **ГДЕ именно запускать:**

```
🖥️ ВАША СИСТЕМА:
C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\

📂 СОЗДАЙТЕ ПАПКУ:
C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge\

📁 СКОПИРУЙТЕ ТУДА:
- mt5_bridge_windows.py
- start_bridge_windows.bat
```

## 🚀 **3 ПРОСТЫХ ШАГА:**

### ✅ **ШАГ 1: Подготовка (1 минута)**
```cmd
# Откройте cmd как Администратор и выполните:
cd "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
mkdir python_bridge
python --version
```

### ✅ **ШАГ 2: Копирование файлов (1 минута)**
Скопируйте из этого проекта в папку `python_bridge`:
- ✅ `mt5_bridge_windows.py` 
- ✅ `start_bridge_windows.bat`

### ✅ **ШАГ 3: Запуск (30 секунд)**
```cmd
# Дважды кликните на файл:
start_bridge_windows.bat

# Увидите:
========================================
MT5 Trading Bridge - Windows Version  
========================================
✓ Running with Python 3.x
Python ML Bridge - WINDOWS ASYNC VERSION
✓ Starting main async loop...
```

## 🎮 **В MT5:**

1. **Скопируйте** `mt5_expert_advisor.mq5` в папку Experts
2. **Компилируйте** в MetaEditor (F7)  
3. **Запустите** на любом графике
4. **Настройте** параметры EA

## 📊 **Результат:**

```
MT5 EA → features_bt.csv → Python Bridge → prediction_bt.txt → MT5 EA
```

**Цикл замкнулся!** 🔄

---

## 🔧 **Если что-то не работает:**

### ❓ **Нет Python?**
```cmd
# Скачайте и установите:
https://python.org/downloads/
# ✅ Поставьте галочку "Add to PATH"
```

### ❓ **Файлы не найдены?**
```cmd
# Проверьте пути:
dir "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
```

### ❓ **Ошибки доступа?**
```cmd
# Запустите cmd как Администратор
```

---

## 🎉 **ГОТОВО!**

**Просто скопируйте 2 файла и запустите bat-файл!**

Система будет работать автоматически:
- 🔄 Читать данные от MT5
- 🧠 Генерировать сигналы  
- 📤 Отправлять обратно в MT5
- 📝 Логировать всё в файл

**Удачной торговли!** 📈🚀