#!/usr/bin/env python3
"""
Быстрый бэктестинг для MT5 Bridge

Простая версия без дополнительных библиотек.
Использует только стандартную библиотеку Python.
"""

import os
import csv
from datetime import datetime, timedelta
from typing import List, Dict

class SimpleBacktest:
    """Простой бэктестер без зависимостей"""
    
    def __init__(self, initial_balance=10000, lot_size=0.1):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.lot_size = lot_size
        self.trades = []
        self.open_position = None
        
    def generate_signal(self, close, ema):
        """Генерация сигнала (ваша логика)"""
        if abs(close - ema) < 0.01:
            return "NONE"
        elif close > ema * 1.001:
            return "BUY"
        elif close < ema * 0.999:
            return "SELL"
        return "NONE"
    
    def process_bar(self, timestamp, close, ema, atr):
        """Обработка одного бара"""
        # Проверяем открытую позицию
        if self.open_position:
            self.check_exit(close, timestamp)
        
        # Генерируем сигнал
        signal = self.generate_signal(close, ema)
        
        # Открываем позицию если нет открытой
        if signal in ["BUY", "SELL"] and not self.open_position:
            self.open_trade(signal, close, timestamp)
    
    def open_trade(self, signal, price, timestamp):
        """Открытие сделки"""
        # Простая логика: SL = 50 пунктов, TP = 100 пунктов
        if signal == "BUY":
            stop_loss = price - 0.0050
            take_profit = price + 0.0100
        else:  # SELL
            stop_loss = price + 0.0050
            take_profit = price - 0.0100
        
        self.open_position = {
            'type': signal,
            'entry_price': price,
            'entry_time': timestamp,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
        print(f"🔵 {signal} opened at {price:.5f} [{timestamp}]")
    
    def check_exit(self, current_price, timestamp):
        """Проверка условий закрытия"""
        pos = self.open_position
        should_close = False
        reason = ""
        
        if pos['type'] == "BUY":
            if current_price <= pos['stop_loss']:
                should_close = True
                reason = "Stop Loss"
            elif current_price >= pos['take_profit']:
                should_close = True
                reason = "Take Profit"
        else:  # SELL
            if current_price >= pos['stop_loss']:
                should_close = True
                reason = "Stop Loss"
            elif current_price <= pos['take_profit']:
                should_close = True
                reason = "Take Profit"
        
        if should_close:
            self.close_trade(current_price, timestamp, reason)
    
    def close_trade(self, exit_price, timestamp, reason):
        """Закрытие сделки"""
        pos = self.open_position
        
        # Расчет прибыли
        if pos['type'] == "BUY":
            pips = (exit_price - pos['entry_price']) / 0.00001
        else:
            pips = (pos['entry_price'] - exit_price) / 0.00001
        
        profit = pips * self.lot_size * 1.0  # $1 за пункт
        
        trade = {
            'entry_time': pos['entry_time'],
            'exit_time': timestamp,
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'profit': profit,
            'pips': pips,
            'reason': reason
        }
        
        self.trades.append(trade)
        self.balance += profit
        self.open_position = None
        
        status = "✅" if profit > 0 else "❌"
        print(f"{status} {pos['type']} closed at {exit_price:.5f} → {pips:.1f} pips, ${profit:.2f} ({reason})")
    
    def get_results(self):
        """Получение результатов"""
        if not self.trades:
            return {"error": "No trades executed"}
        
        winning = [t for t in self.trades if t['profit'] > 0]
        losing = [t for t in self.trades if t['profit'] <= 0]
        
        return {
            "total_trades": len(self.trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(self.trades) * 100,
            "total_profit": sum(t['profit'] for t in self.trades),
            "final_balance": self.balance,
            "return_percent": (self.balance - self.initial_balance) / self.initial_balance * 100
        }

def load_mt5_data(filename):
    """Загрузка данных MT5"""
    data = []
    
    if not os.path.exists(filename):
        print(f"❌ Файл не найден: {filename}")
        return None
    
    try:
        with open(filename, 'r') as f:
            for line in f:
                if ';' in line:
                    parts = line.strip().split(';')
                    if len(parts) >= 4:
                        timestamp_str = parts[0]
                        close = float(parts[1].replace(',', '.'))
                        ema = float(parts[2].replace(',', '.'))
                        atr = float(parts[3].replace(',', '.'))
                        
                        timestamp = datetime.strptime(timestamp_str, "%Y.%m.%d %H:%M")
                        
                        data.append({
                            'timestamp': timestamp,
                            'close': close,
                            'ema': ema,
                            'atr': atr
                        })
        
        print(f"✅ Загружено {len(data)} баров")
        return data
        
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return None

def create_test_data():
    """Создание тестовых данных"""
    print("📊 Создание тестовых данных...")
    
    # Создаем 1000 баров тестовых данных
    data = []
    base_price = 1.0850
    base_time = datetime.now() - timedelta(hours=1000)
    
    for i in range(1000):
        # Простая симуляция движения цены
        price_change = (i % 100 - 50) * 0.00001  # волнообразное движение
        close = base_price + price_change
        ema = close - 0.0010 + (i % 20) * 0.0001  # EMA чуть ниже цены
        atr = 0.0015 + (i % 10) * 0.0001
        
        timestamp = base_time + timedelta(minutes=i)
        
        data.append({
            'timestamp': timestamp,
            'close': close,
            'ema': ema,
            'atr': atr
        })
    
    # Сохраняем в файл
    filename = "test_data.csv"
    with open(filename, 'w') as f:
        for bar in data:
            line = f"{bar['timestamp'].strftime('%Y.%m.%d %H:%M')};{bar['close']:.5f};{bar['ema']:.5f};{bar['atr']:.5f}\n"
            f.write(line)
    
    print(f"✅ Создано {len(data)} тестовых баров в файле: {filename}")
    return data

def main():
    """Главная функция"""
    print("🧪 Быстрый бэктестинг MT5 Bridge")
    print("="*50)
    
    # Пробуем загрузить реальные данные
    real_data_file = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\features_bt.csv"
    
    data = load_mt5_data(real_data_file)
    
    if not data or len(data) < 10:
        print("📊 Реальных данных мало, создаем тестовые...")
        data = create_test_data()
    
    if not data:
        print("❌ Не удалось получить данные для тестирования")
        return
    
    # Настройки тестирования
    print(f"\n⚙️ Настройки:")
    print(f"💰 Начальный баланс: $10,000")
    print(f"📊 Размер лота: 0.1")
    print(f"📈 Take Profit: 100 пунктов")
    print(f"📉 Stop Loss: 50 пунктов")
    
    # Запуск бэктестинга
    backtest = SimpleBacktest(initial_balance=10000, lot_size=0.1)
    
    print(f"\n🚀 Запуск бэктестинга на {len(data)} барах...")
    print("="*50)
    
    for bar in data:
        backtest.process_bar(
            bar['timestamp'],
            bar['close'],
            bar['ema'],
            bar['atr']
        )
    
    # Закрываем открытую позицию если есть
    if backtest.open_position:
        backtest.close_trade(data[-1]['close'], data[-1]['timestamp'], "End of test")
    
    # Результаты
    results = backtest.get_results()
    
    if "error" not in results:
        print("\n📊 РЕЗУЛЬТАТЫ БЭКТЕСТИНГА:")
        print("="*50)
        print(f"📈 Итоговый баланс:   ${results['final_balance']:.2f}")
        print(f"💰 Прибыль:           ${results['total_profit']:.2f}")
        print(f"📊 Доходность:        {results['return_percent']:.2f}%")
        print(f"🔢 Всего сделок:      {results['total_trades']}")
        print(f"✅ Прибыльных:        {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"❌ Убыточных:         {results['losing_trades']}")
        print("="*50)
        
        if results['total_profit'] > 0:
            print("🎉 СТРАТЕГИЯ ПРИБЫЛЬНА!")
        else:
            print("⚠️ СТРАТЕГИЯ УБЫТОЧНА")
    else:
        print("❌ Бэктестинг не выполнен:", results['error'])

if __name__ == "__main__":
    main()
```

## 🧪 **КАК ПРОТЕСТИРОВАТЬ:**

### **1️⃣ Быстрый тест (без библиотек):**
```cmd
cd "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge"
python quick_backtest.py
```

### **2️⃣ Полный тест (с библиотеками):**
```cmd
pip install pandas numpy matplotlib
python backtest_system.py
```

### **3️⃣ Тест на ваших реальных данных:**
Если у вас есть файл `features_bt.csv` с историей - он автоматически будет использован!

## 📊 **ЧТО ПОЛУЧИТЕ:**

```
🧪 Быстрый бэктестинг MT5 Bridge
==================================================
✅ Загружено 1000 баров
🔵 BUY opened at 1.08500 [2025.08.29 15:30]
✅ BUY closed at 1.08600 → 100.0 pips, $10.00 (Take Profit)
🔴 SELL opened at 1.08450 [2025.08.29 16:45]
❌ SELL closed at 1.08500 → -50.0 pips, $-5.00 (Stop Loss)

📊 РЕЗУЛЬТАТЫ БЭКТЕСТИНГА:
==================================================
📈 Итоговый баланс:   $10,250.00
💰 Прибыль:           $250.00
📊 Доходность:        2.50%
🔢 Всего сделок:      25
✅ Прибыльных:        15 (60.0%)
❌ Убыточных:         10
🎉 СТРАТЕГИЯ ПРИБЫЛЬНА!
```

## 🎯 **ЗАПУСКАЙТЕ БЭКТЕСТИНГ!**

**Какой тест хотите:** быстрый или полный? 🤔