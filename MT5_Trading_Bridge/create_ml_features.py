#!/usr/bin/env python3
"""
Создание ml_features.csv для ULTIMATE CRYSTAL PERFECT системы
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

def create_ml_features_dataset(n_bars=10000):
    """Создание полного ML датасета с техническими индикаторами"""
    
    print(f"🔧 Создание ML features датасета ({n_bars} баров)...")
    
    # Базовые OHLCV данные
    np.random.seed(42)
    start_price = 50000.0
    start_time = datetime.now() - timedelta(minutes=n_bars)
    
    data = []
    current_price = start_price
    
    for i in range(n_bars):
        timestamp = start_time + timedelta(minutes=i)
        
        # Случайное изменение цены с трендом
        trend = np.sin(i * 2 * np.pi / 1000) * 0.001  # Циклический тренд
        noise = np.random.normal(0, 0.002)  # Шум
        change = trend + noise
        
        current_price *= (1 + change)
        current_price = max(current_price, 1000)  # Минимальная цена
        
        # OHLC
        volatility = abs(np.random.normal(0, 0.001))
        high = current_price * (1 + volatility)
        low = current_price * (1 - volatility)
        
        if i == 0:
            open_price = current_price
        else:
            open_price = data[i-1]['close']
        
        # Корректируем OHLC
        actual_high = max(open_price, current_price, high)
        actual_low = min(open_price, current_price, low)
        
        volume = np.random.uniform(100, 2000)
        
        data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'open': round(open_price, 2),
            'high': round(actual_high, 2),
            'low': round(actual_low, 2),
            'close': round(current_price, 2),
            'volume': round(volume, 2)
        })
    
    df = pd.DataFrame(data)
    
    # Добавляем технические индикаторы
    print("📊 Добавляем технические индикаторы...")
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd_main'] = ema12 - ema26
    df['macd_signal'] = df['macd_main'].ewm(span=9).mean()
    
    # Bollinger Bands
    bb_ma = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    bb_upper = bb_ma + (bb_std * 2)
    bb_lower = bb_ma - (bb_std * 2)
    df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
    
    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    df['stoch_main'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
    df['stoch_signal'] = df['stoch_main'].rolling(3).mean()
    
    # EMAs
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['ema_21'] = df['close'].ewm(span=21).mean()
    
    # ATR
    df['tr'] = np.maximum(df['high'] - df['low'], 
                         np.maximum(abs(df['high'] - df['close'].shift(1)),
                                   abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    
    # Volatility
    df['volatility'] = df['close'].pct_change().rolling(20).std()
    
    # Target (future return)
    df['target'] = df['close'].pct_change().shift(-1)
    
    # Заполняем NaN
    df = df.fillna(method='ffill').fillna(0)
    
    # Убираем infinity
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.fillna(0)
    
    print(f"✅ Создан датасет: {len(df)} строк, {df.shape[1]} колонок")
    print(f"📊 Период: {df['timestamp'].iloc[0]} - {df['timestamp'].iloc[-1]}")
    print(f"💰 Цены: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    return df

def main():
    # Создаем директорию
    base_dir = os.environ.get("CRYSTAL_DATA_DIR", ".")
    data_dir = Path(base_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем данные
    df = create_ml_features_dataset(10000)
    
    # Сохраняем
    features_file = data_dir / "ml_features.csv"
    df.to_csv(features_file, sep=';', index=False)
    
    print(f"📁 Сохранено в: {features_file}")
    print(f"📋 Первые 3 строки:")
    print(df.head(3)[['timestamp', 'close', 'rsi', 'macd_main', 'bb_position', 'target']].to_string())

if __name__ == "__main__":
    main()