#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🚀 СОЗДАНИЕ РАСШИРЕННОЙ M5 ИСТОРИИ ДЛЯ CRYSTAL TANK
📊 Генерация 100,000+ M5 баров (~1 год истории)
🎯 Цель: стресс-тест системы на длинной истории
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_extended_m5_crypto_data(n_m5_bars=100000):
    """
    Создает расширенные M5 данные для более надежного тестирования
    
    Args:
        n_m5_bars: количество M5 баров (100k = ~1 год)
    
    Returns:
        pd.DataFrame: M5 данные с техническими индикаторами
    """
    print(f"🚀 ГЕНЕРАЦИЯ {n_m5_bars:,} M5 БАРОВ")
    print(f"📅 Период: ~{n_m5_bars / (24*12*30):.1f} месяцев")
    
    # Установка seed для воспроизводимости
    np.random.seed(42)
    
    # Начальные параметры для BTC M5
    start_time = datetime.now() - timedelta(minutes=n_m5_bars * 5)
    base_price = 45000.0
    
    # M5 волатильность (меньше чем M1)
    volatility = 0.0015  # 0.15% за 5 минут
    trend_strength = 0.00005  # слабый тренд
    
    m5_data = []
    current_price = base_price
    
    print("📊 Генерация M5 OHLC...")
    for i in range(n_m5_bars):
        if i % 10000 == 0:
            print(f"   📈 Прогресс: {i/n_m5_bars*100:.1f}%")
            
        # Тренд + случайное движение
        trend = trend_strength * np.sin(i / 1000)  # медленный тренд
        noise = np.random.normal(0, volatility)
        price_change = trend + noise
        
        # OHLC для M5 бара
        open_price = current_price
        high_price = open_price * (1 + abs(price_change) + np.random.exponential(0.0005))
        low_price = open_price * (1 - abs(price_change) - np.random.exponential(0.0005))
        close_price = open_price * (1 + price_change)
        
        # Обновляем текущую цену
        current_price = close_price
        
        timestamp = start_time + timedelta(minutes=i * 5)
        
        m5_data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.uniform(10, 1000)  # объем
        })
    
    df_ohlc = pd.DataFrame(m5_data)
    
    print("🔧 Расчет технических индикаторов M5...")
    
    # Технические индикаторы для M5
    df = df_ohlc.copy()
    
    # RSI (14 периодов M5 = 70 минут)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD (12,26,9 для M5)
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd_main'] = ema12 - ema26
    df['macd_signal'] = df['macd_main'].ewm(span=9).mean()
    
    # Bollinger Bands (20 периодов M5)
    bb_period = 20
    bb_std = 2
    bb_ma = df['close'].rolling(bb_period).mean()
    bb_stddev = df['close'].rolling(bb_period).std()
    df['bb_upper'] = bb_ma + bb_std * bb_stddev
    df['bb_lower'] = bb_ma - bb_std * bb_stddev
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Stochastic (14,3,3 для M5)
    low_min = df['low'].rolling(14).min()
    high_max = df['high'].rolling(14).max()
    k_percent = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['stoch_main'] = k_percent.rolling(3).mean()
    
    # EMA (9 и 21 для M5)
    df['ema_9'] = df['close'].ewm(span=9).mean()
    df['ema_21'] = df['close'].ewm(span=21).mean()
    
    # ATR (14 периодов M5)
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Волатильность (20 периодов M5)
    df['volatility'] = df['close'].pct_change().rolling(20).std()
    
    # Временные признаки для M5
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp_dt'].dt.hour
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    
    # Лондонская сессия (08:00-17:00 UTC)
    df['london_session'] = ((df['hour'] >= 8) & (df['hour'] < 17)).astype(int)
    
    # Лагированные признаки (важно для M5!)
    for col in ['rsi', 'macd_main', 'bb_position', 'stoch_main', 'atr', 'volatility']:
        df[f'{col}_lag1'] = df[col].shift(1)
        df[f'{col}_lag2'] = df[col].shift(2)
    
    # Target: следующий 5-минутный return (сдвиг назад)
    df['future_return'] = df['close'].pct_change().shift(-1)
    
    # Классификация для M5 (более мягкие пороги)
    target_threshold = 0.0008  # 0.08% для M5
    df['target'] = 0  # hold
    df.loc[df['future_return'] > target_threshold, 'target'] = 1   # buy
    df.loc[df['future_return'] < -target_threshold, 'target'] = -1  # sell
    
    # Удаляем временные колонки
    df = df.drop(['timestamp_dt', 'future_return', 'open', 'high', 'low', 'volume'], axis=1)
    
    # Финальная очистка
    df = df.dropna().reset_index(drop=True)
    
    print(f"✅ Создано {len(df):,} чистых M5 баров")
    print(f"🎯 Target распределение: {df['target'].value_counts().to_dict()}")
    
    return df

def main():
    """Основная функция создания расширенных M5 данных"""
    print("🚀 СОЗДАНИЕ РАСШИРЕННОЙ M5 ИСТОРИИ")
    print("📊 100,000+ баров для стресс-теста системы")
    print("🎯 Цель: проверить стабильность на длинной истории")
    
    # Создаем 120,000 M5 баров (~1.2 года)
    df_extended = create_extended_m5_crypto_data(120000)
    
    # Путь к данным
    data_dir = os.environ.get("CRYSTAL_DATA_DIR", 
                             os.path.expanduser(r"~\AppData\Roaming\MetaQuotes\Terminal\Common\Files"))
    
    # Бэкап старых данных
    old_file = os.path.join(data_dir, "ml_features.csv")
    backup_file = os.path.join(data_dir, "ml_features_m5_short_backup.csv")
    
    if os.path.exists(old_file):
        os.rename(old_file, backup_file)
        print(f"📦 Короткие M5 данные сохранены: ml_features_m5_short_backup.csv")
    
    # Сохраняем новые расширенные данные
    new_file = os.path.join(data_dir, "ml_features.csv")
    df_extended.to_csv(new_file, sep=';', index=False, encoding='utf-8')
    
    print(f"✅ Расширенные M5 данные: {new_file}")
    print(f"📊 Размер: {len(df_extended):,} баров (~{len(df_extended)/(24*12*30):.1f} месяцев)")
    
    # Показываем образец
    print(f"\n📋 Образец расширенных M5 данных:")
    sample_cols = ['timestamp', 'close', 'rsi', 'macd_main', 'bb_position', 'target']
    print(df_extended[sample_cols].head(3).to_string())
    
    print(f"\n🎯 СЛЕДУЮЩИЕ ШАГИ:")
    print(f"🚀 1. Запустите: run_btc_m5_margin.bat")
    print(f"📊 2. Ожидаем: стабильные результаты на 120k баров")
    print(f"🛡️3. Затем: стресс-тест с высокими издержками")
    print(f"💎 4. Финал: подготовка к реальному деплою")

if __name__ == "__main__":
    main()