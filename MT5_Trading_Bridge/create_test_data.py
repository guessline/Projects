#!/usr/bin/env python3
"""
Создание тестовых данных для проверки ULTIMATE CRYSTAL PERFECT системы
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_test_btc_data(n_bars=1000):
    """Создание реалистичных тестовых данных BTC"""
    
    # Начальная цена
    start_price = 50000.0
    
    # Временные метки (каждую минуту)
    start_time = datetime.now() - timedelta(minutes=n_bars)
    timestamps = [start_time + timedelta(minutes=i) for i in range(n_bars)]
    
    # Генерация цен с волатильностью
    np.random.seed(42)  # Для воспроизводимости
    
    # Случайные изменения цены
    price_changes = np.random.normal(0, 0.001, n_bars)  # 0.1% волатильность
    
    # Добавим трендовые движения
    trend = np.sin(np.arange(n_bars) * 2 * np.pi / 100) * 0.002
    price_changes += trend
    
    # Генерация цен
    prices = [start_price]
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 100))  # Минимальная цена
    
    # OHLC данные
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        # Генерируем OHLC вокруг close
        volatility = abs(np.random.normal(0, 0.0005))  # Внутридневная волатильность
        
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1]  # Open = предыдущий close
        
        # Корректируем OHLC логику
        actual_high = max(open_price, close, high)
        actual_low = min(open_price, close, low)
        
        # Объем (случайный, но реалистичный)
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'open': round(open_price, 2),
            'high': round(actual_high, 2),
            'low': round(actual_low, 2),
            'close': round(close, 2),
            'volume': round(volume, 2)
        })
    
    df = pd.DataFrame(data)
    return df

def main():
    print("🔧 Создание тестовых данных BTC...")
    
    # Создаем тестовые данные
    df = create_test_btc_data(1000)
    
    # Сохраняем
    df.to_csv('btc_history_100k.csv', index=False)
    
    print(f"✅ Создано {len(df)} тестовых баров")
    print(f"📊 Период: {df['timestamp'].iloc[0]} - {df['timestamp'].iloc[-1]}")
    print(f"💰 Цены: {df['close'].min():.2f} - {df['close'].max():.2f}")
    print(f"📁 Сохранено в: btc_history_100k.csv")
    
    # Показываем первые строки
    print("\n📋 Первые 3 строки:")
    print(df.head(3).to_string())

if __name__ == "__main__":
    main()