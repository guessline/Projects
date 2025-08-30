# 🛠️ **ГДЕ И КАК ЗАПУСКАТЬ - Пошаговая Инструкция**

## 🖥️ **Архитектура системы:**

```
┌─────────────────┐    файлы    ┌─────────────────┐
│   WINDOWS PC    │◄──────────►│   LINUX SERVER  │
│                 │             │                 │
│ MetaTrader 5    │             │ Python Bridge   │
│ Expert Advisor  │             │ mt5_bridge_v2   │
│                 │             │                 │
│ features_bt.csv │◄────────────┤ prediction.txt  │
│ prediction.txt  │────────────►│ JSON metadata   │
└─────────────────┘             └─────────────────┘
```

## 🎯 **Варианты установки:**

### 🥇 **ВАРИАНТ 1: Всё на одном Windows ПК (Рекомендуется)**

#### 📍 **Где запускать:**
```
C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\
```

#### 🔧 **Установка:**

1. **Скопируйте Python файлы в папку MT5:**
   ```cmd
   # Создайте папку для Python
   mkdir "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge"
   
   # Скопируйте файлы
   copy mt5_bridge_v2.py "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge\"
   copy config.py "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge\"
   ```

2. **Создайте Windows batch файл для запуска:**
   ```cmd
   # Файл: start_bridge_windows.bat
   @echo off
   cd /d "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge"
   set MT5_FEATURES_PATH=C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\features_bt.csv
   set MT5_PREDICTION_PATH=C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\prediction_bt.txt
   python mt5_bridge_v2.py
   pause
   ```

3. **Установите Expert Advisor:**
   ```
   C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\<TERMINAL_ID>\MQL5\Experts\mt5_expert_advisor.mq5
   ```

### 🥈 **ВАРИАНТ 2: Python на отдельном сервере**

#### 📍 **Где запускать:**
- **MT5**: Windows ПК (как обычно)
- **Python**: Linux сервер или VPS

#### 🔧 **Установка:**

1. **На Linux сервере:**
   ```bash
   # Скопируйте проект
   scp -r MT5_Trading_Bridge/ user@server:/home/user/
   
   # На сервере
   cd /home/user/MT5_Trading_Bridge
   chmod +x *.py *.sh
   ```

2. **Синхронизация файлов между Windows и Linux:**
   ```bash
   # Вариант A: Сетевая папка (SMB/CIFS)
   sudo mount -t cifs //windows-pc/mt5-share /mnt/mt5 -o username=AdmVps
   
   # Вариант B: rsync синхронизация
   rsync -av user@windows-pc:/path/to/mt5/files/ ~/mt5_data/
   
   # Вариант C: FTP/SFTP
   ```

### 🥉 **ВАРИАНТ 3: Облачное решение**

#### 📍 **Где запускать:**
- **MT5**: Windows ПК
- **Python**: AWS/Google Cloud/DigitalOcean

## 🎯 **МОЯ РЕКОМЕНДАЦИЯ: ВАРИАНТ 1**

Для вашего случая лучше всего **запускать всё на одном Windows ПК**, потому что:

✅ **Простота** - нет сетевых задержек  
✅ **Надежность** - прямой доступ к файлам  
✅ **Скорость** - мгновенная синхронизация  
✅ **Отладка** - легко контролировать процесс  

## 📋 **Пошаговая установка (Windows):**

### Шаг 1: Подготовка Python на Windows
```cmd
# Проверьте Python
python --version

# Если нет Python, скачайте с python.org
# Установите с галочкой "Add to PATH"
```

### Шаг 2: Создайте структуру
```cmd
cd "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
mkdir python_bridge
cd python_bridge
```

### Шаг 3: Скопируйте файлы
```cmd
# Скопируйте эти файлы в папку python_bridge:
copy mt5_bridge_windows.py python_bridge\
copy start_bridge_windows.bat python_bridge\
```

### Шаг 4: Установите Expert Advisor
```cmd
# Скопируйте в папку Experts:
copy mt5_expert_advisor.mq5 "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\<TERMINAL_ID>\MQL5\Experts\"
```

### Шаг 5: Запуск
```cmd
# Дважды кликните на файл:
start_bridge_windows.bat

# Или из командной строки:
cd "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge"
start_bridge_windows.bat
```

## 🔥 **ГОТОВЫЕ КОМАНДЫ ДЛЯ КОПИРОВАНИЯ:**

### Создание структуры (выполните в cmd):
```cmd
cd "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
mkdir python_bridge
echo Папка создана: %CD%\python_bridge
```

### Проверка Python:
```cmd
python --version
python -c "print('Python работает!')"
```

## 📂 **Итоговая структура на Windows:**

```
C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\
├── python_bridge\
│   ├── mt5_bridge_windows.py      ← Основной мост
│   ├── start_bridge_windows.bat   ← Запуск
│   └── bridge.log                 ← Логи
├── features_bt.csv                ← Входные данные (создает EA)
├── prediction_bt.txt              ← Сигналы (создает Python)
└── prediction_bt.json             ← Метаданные (создает Python)
```

## ⚡ **БЫСТРЫЙ СТАРТ:**

1. **Установите Python** (если нет): https://python.org
2. **Скопируйте файлы** в папку MT5
3. **Запустите**: `start_bridge_windows.bat`
4. **В MT5**: установите и запустите `mt5_expert_advisor.mq5`

## 🎯 **Альтернативные варианты:**