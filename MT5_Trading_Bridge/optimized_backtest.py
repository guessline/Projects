#!/usr/bin/env python3
"""
Оптимизированный бэктестинг с улучшенными параметрами
Анализ показал проблемы - исправляем их!
"""

import os
import math
from datetime import datetime, timedelta

class OptimizedBacktest:
    """Оптимизированный бэктестер с улучшенным риск-менеджментом"""
    
    def __init__(self, initial_balance=10000, lot_size=0.1):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.lot_size = lot_size
        self.trades = []
        self.open_position = None
        self.signal_count = {"BUY": 0, "SELL": 0, "NONE": 0}
        
        # УЛУЧШЕННЫЕ ПАРАМЕТРЫ
        self.stop_loss_pips = 25      # Уменьшили SL с 50 до 25
        self.take_profit_pips = 50    # Уменьшили TP с 100 до 50 (Risk/Reward 1:2)
        self.min_signal_strength = 8  # Увеличили порог с 5 до 8 пипсов
        self.max_atr_multiplier = 3   # Не торгуем при высокой волатильности
        
    def generate_signal(self, close, ema, atr):
        """УЛУЧШЕННАЯ генерация сигнала с фильтрами"""
        diff_pips = abs(close - ema) / 0.00001
        atr_pips = atr / 0.00001
        
        # ФИЛЬТР 1: Минимальная разница
        if diff_pips < self.min_signal_strength:
            return "NONE", f"слабый сигнал ({diff_pips:.1f} < {self.min_signal_strength} пипсов)"
        
        # ФИЛЬТР 2: Волатильность (не торгуем при высоком ATR)
        if atr_pips > self.stop_loss_pips * self.max_atr_multiplier:
            return "NONE", f"высокая волатильность (ATR {atr_pips:.1f} > {self.stop_loss_pips * self.max_atr_multiplier})"
        
        # ОСНОВНАЯ ЛОГИКА
        if (close - ema) / 0.00001 > self.min_signal_strength:
            return "BUY", f"цена выше EMA на {(close-ema)/0.00001:.1f} пипсов"
        elif (ema - close) / 0.00001 > self.min_signal_strength:
            return "SELL", f"цена ниже EMA на {(ema-close)/0.00001:.1f} пипсов"
        
        return "NONE", f"недостаточная разница ({diff_pips:.1f} пипсов)"
    
    def process_bar(self, timestamp, close, ema, atr):
        """Обработка бара с улучшенной логикой"""
        # Проверяем открытую позицию
        if self.open_position:
            self.check_exit(close, timestamp)
        
        # Генерируем сигнал только если нет позиции
        if not self.open_position:
            signal, reason = self.generate_signal(close, ema, atr)
            self.signal_count[signal] += 1
            
            if signal != "NONE":
                print(f"🔍 {signal}: {reason}")
                self.open_trade(signal, close, timestamp, atr)
    
    def open_trade(self, signal, price, timestamp, atr):
        """Открытие сделки с адаптивными SL/TP"""
        # АДАПТИВНЫЙ STOP LOSS на основе ATR
        atr_pips = atr / 0.00001
        adaptive_sl = max(self.stop_loss_pips, atr_pips * 1.5)  # минимум 25 пипсов или 1.5*ATR
        adaptive_tp = adaptive_sl * 2  # соотношение 1:2
        
        if signal == "BUY":
            stop_loss = price - adaptive_sl * 0.00001
            take_profit = price + adaptive_tp * 0.00001
        else:  # SELL
            stop_loss = price + adaptive_sl * 0.00001
            take_profit = price - adaptive_tp * 0.00001
        
        self.open_position = {
            'type': signal,
            'entry_price': price,
            'entry_time': timestamp,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'sl_pips': adaptive_sl,
            'tp_pips': adaptive_tp
        }
        
        print(f"🔵 {signal} opened at {price:.5f} [{timestamp.strftime('%H:%M')}]")
        print(f"   SL: {stop_loss:.5f} ({adaptive_sl:.0f} pips), TP: {take_profit:.5f} ({adaptive_tp:.0f} pips)")
    
    def check_exit(self, current_price, timestamp):
        """Проверка выхода"""
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
        
        if pos['type'] == "BUY":
            pips = (exit_price - pos['entry_price']) / 0.00001
        else:
            pips = (pos['entry_price'] - exit_price) / 0.00001
        
        profit = pips * self.lot_size * 1.0
        
        trade = {
            'entry_time': pos['entry_time'],
            'exit_time': timestamp,
            'type': pos['type'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'profit': profit,
            'pips': pips,
            'reason': reason,
            'sl_pips': pos['sl_pips'],
            'tp_pips': pos['tp_pips']
        }
        
        self.trades.append(trade)
        self.balance += profit
        self.open_position = None
        
        status = "✅" if profit > 0 else "❌"
        print(f"{status} {pos['type']} closed at {exit_price:.5f} → {pips:.1f} pips, ${profit:.2f} ({reason})")
    
    def get_results(self):
        """Расширенные результаты"""
        if not self.trades:
            return {"error": "No trades executed"}
        
        winning = [t for t in self.trades if t['profit'] > 0]
        losing = [t for t in self.trades if t['profit'] <= 0]
        
        # Дополнительная статистика
        max_win = max([t['profit'] for t in winning]) if winning else 0
        max_loss = min([t['profit'] for t in losing]) if losing else 0
        
        return {
            "total_trades": len(self.trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(self.trades) * 100,
            "total_profit": sum(t['profit'] for t in self.trades),
            "final_balance": self.balance,
            "return_percent": (self.balance - self.initial_balance) / self.initial_balance * 100,
            "avg_win": sum(t['profit'] for t in winning) / len(winning) if winning else 0,
            "avg_loss": sum(t['profit'] for t in losing) / len(losing) if losing else 0,
            "max_win": max_win,
            "max_loss": max_loss,
            "profit_factor": abs(sum(t['profit'] for t in winning) / sum(t['profit'] for t in losing)) if losing else float('inf')
        }

def create_realistic_forex_data():
    """Создание реалистичных форекс данных"""
    print("📊 Создание реалистичных форекс данных...")
    
    data = []
    base_price = 1.0850
    base_time = datetime.now() - timedelta(hours=100)
    
    for i in range(100):
        # Создаем реалистичные движения
        if i < 25:  # Восходящий тренд
            trend = i * 0.0002
            ema_lag = i * 0.00015  # EMA отстает
        elif i < 50:  # Боковик
            trend = 25 * 0.0002 + math.sin(i/5) * 0.0001
            ema_lag = trend
        elif i < 75:  # Нисходящий тренд  
            trend = 25 * 0.0002 - (i-50) * 0.0002
            ema_lag = 25 * 0.00015 - (i-50) * 0.00015
        else:  # Восстановление
            trend = -25 * 0.0002 + (i-75) * 0.0003
            ema_lag = -25 * 0.00015 + (i-75) * 0.0002
        
        close = base_price + trend + (i % 3 - 1) * 0.00003  # небольшой шум
        ema = base_price + ema_lag
        atr = 0.00015 + (i % 5) * 0.00003  # переменная волатильность
        
        timestamp = base_time + timedelta(minutes=i*15)  # каждые 15 минут
        
        data.append({
            'timestamp': timestamp,
            'close': close,
            'ema': ema,
            'atr': atr
        })
    
    print(f"✅ Создано {len(data)} реалистичных форекс баров")
    return data

def main():
    """Главная функция"""
    print("🎯 ОПТИМИЗИРОВАННЫЙ бэктестинг MT5 Bridge")
    print("="*60)
    
    # Создаем реалистичные данные
    data = create_realistic_forex_data()
    
    # Улучшенные настройки
    print(f"\n⚙️ УЛУЧШЕННЫЕ настройки:")
    print(f"💰 Начальный баланс: $10,000")
    print(f"📊 Размер лота: 0.1")
    print(f"📉 Stop Loss: 25 пипсов (адаптивный)")
    print(f"📈 Take Profit: 50 пипсов (Risk/Reward 1:2)")
    print(f"🎯 Минимальный сигнал: 8 пипсов от EMA")
    print(f"🌪️ Фильтр волатильности: ATR < 75 пипсов")
    
    # Запуск оптимизированного теста
    backtest = OptimizedBacktest(initial_balance=10000, lot_size=0.1)
    
    print(f"\n🚀 Запуск ОПТИМИЗИРОВАННОГО бэктестинга...")
    print("="*60)
    
    for bar in data:
        backtest.process_bar(
            bar['timestamp'],
            bar['close'],
            bar['ema'],
            bar['atr']
        )
    
    # Закрываем открытую позицию
    if backtest.open_position:
        backtest.close_trade(data[-1]['close'], data[-1]['timestamp'], "End of test")
    
    print(f"\n📈 Статистика сигналов:")
    print(f"🔵 BUY сигналов: {backtest.signal_count['BUY']}")
    print(f"🔴 SELL сигналов: {backtest.signal_count['SELL']}")
    print(f"⚪ NONE сигналов: {backtest.signal_count['NONE']}")
    
    # Результаты
    results = backtest.get_results()
    
    if "error" not in results:
        print("\n📊 РЕЗУЛЬТАТЫ ОПТИМИЗИРОВАННОГО БЭКТЕСТИНГА:")
        print("="*60)
        print(f"📈 Итоговый баланс:   ${results['final_balance']:.2f}")
        print(f"💰 Прибыль:           ${results['total_profit']:.2f}")
        print(f"📊 Доходность:        {results['return_percent']:.2f}%")
        print(f"🔢 Всего сделок:      {results['total_trades']}")
        print(f"✅ Прибыльных:        {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"❌ Убыточных:         {results['losing_trades']}")
        print(f"💵 Средняя прибыль:   ${results['avg_win']:.2f}")
        print(f"💸 Средний убыток:    ${results['avg_loss']:.2f}")
        print(f"🏆 Максимальная прибыль: ${results['max_win']:.2f}")
        print(f"💥 Максимальный убыток:  ${results['max_loss']:.2f}")
        print(f"⚖️ Profit Factor:     {results['profit_factor']:.2f}")
        print("="*60)
        
        # АНАЛИЗ КАЧЕСТВА СТРАТЕГИИ
        if results['profit_factor'] > 1.5:
            print("🎉 ОТЛИЧНАЯ СТРАТЕГИЯ! (Profit Factor > 1.5)")
        elif results['profit_factor'] > 1.2:
            print("✅ ХОРОШАЯ СТРАТЕГИЯ! (Profit Factor > 1.2)")
        elif results['profit_factor'] > 1.0:
            print("⚠️ СЛАБО ПРИБЫЛЬНАЯ СТРАТЕГИЯ")
        else:
            print("❌ УБЫТОЧНАЯ СТРАТЕГИЯ")
            
        # РЕКОМЕНДАЦИИ
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        if results['win_rate'] > 70:
            print("✅ Высокая точность - можно увеличить TP")
        if abs(results['avg_loss']) > results['avg_win'] * 2:
            print("⚠️ Большие убытки - уменьшить SL")
        if results['total_trades'] < 10:
            print("📊 Мало сделок - смягчить условия входа")
            
    else:
        print("❌ Бэктестинг не выполнен:", results['error'])
    
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()