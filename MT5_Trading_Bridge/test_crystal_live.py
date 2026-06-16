#!/usr/bin/env python3
"""
Тест live inference для ULTIMATE CRYSTAL PERFECT системы
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime

def test_live_inference():
    """Тестируем live предсказания"""
    
    print("🧪 Тестируем ULTIMATE CRYSTAL PERFECT live inference...")
    
    # Загружаем обученную модель
    try:
        with open('ultimate_crystal_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
        
        print("✅ Модель загружена успешно")
        print(f"📊 Метаданные: {len(model_data['metadata'])} полей")
        
    except FileNotFoundError:
        print("❌ Модель не найдена! Сначала запустите обучение.")
        return
    
    # Создаем тестовые live данные
    np.random.seed(123)  # Другой seed для разнообразия
    
    # Генерируем последние 100 баров для контекста
    start_price = 51000.0
    timestamps = [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    
    data = []
    current_price = start_price
    
    for i in range(100):
        # Случайное изменение цены
        change = np.random.normal(0, 0.001)
        current_price *= (1 + change)
        
        # OHLC
        volatility = abs(np.random.normal(0, 0.0005))
        high = current_price * (1 + volatility)
        low = current_price * (1 - volatility)
        open_price = current_price * (1 + np.random.normal(0, 0.0002))
        
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(current_price, 2),
            'volume': round(volume, 2)
        })
    
    live_df = pd.DataFrame(data)
    print(f"📈 Создано {len(live_df)} live баров")
    print(f"💰 Текущая цена: {live_df['close'].iloc[-1]:.2f}")
    
    # Импортируем класс и создаем экземпляр
    from ultimate_crystal_perfect_v2 import UltimateCrystalPerfectML
    
    ml_system = UltimateCrystalPerfectML()
    ml_system.model = model_data['model']
    ml_system.scaler = model_data['scaler']
    ml_system.metadata = model_data['metadata']
    
    # Тестируем предсказание
    try:
        prediction = ml_system.predict_live_perfect(live_df)
        
        print("\n🎯 LIVE ПРЕДСКАЗАНИЕ:")
        print(f"📊 Сигнал: {prediction['signal']} ({'BUY' if prediction['signal'] == 1 else 'SELL' if prediction['signal'] == -1 else 'HOLD'})")
        print(f"🎯 Уверенность: {prediction['confidence']:.3f}")
        print(f"📈 Proba BUY: {prediction['proba_buy']:.3f}")
        print(f"📉 Proba SELL: {prediction['proba_sell']:.3f}")
        print(f"⏰ Время: {prediction['timestamp']}")
        
        # Пороги
        buy_thresh = ml_system.metadata['avg_buy_threshold']
        sell_thresh = ml_system.metadata['avg_sell_threshold']
        print(f"\n🎚️ Пороги: BUY={buy_thresh:.3f}, SELL={sell_thresh:.3f}")
        
        print("\n✅ Live inference работает корректно!")
        
    except Exception as e:
        print(f"❌ Ошибка live предсказания: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_live_inference()