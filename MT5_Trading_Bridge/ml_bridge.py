#!/usr/bin/env python3
"""
ML Bridge для MT5 - Реальное машинное обучение

Заменяет простую EMA логику на настоящие ML предсказания.
Использует обученную модель для генерации торговых сигналов.
"""

import os
import sys
import pickle
import time
import json
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings('ignore')

# Проверяем ML библиотеки
try:
    import pandas as pd
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    print("⚠️ ML библиотеки не установлены. Переключаюсь на простую логику.")
    ML_AVAILABLE = False

class MLBridge:
    """ML Bridge для реального времени"""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            self.data_dir = Path(r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
        else:
            self.data_dir = Path(data_dir)
            
        # Файлы
        self.features_file = self.data_dir / "ml_features.csv"
        self.predictions_file = self.data_dir / "ml_predictions.txt"
        self.model_file = self.data_dir / "trading_model.pkl"
        self.scaler_file = self.data_dir / "feature_scaler.pkl"
        self.feature_names_file = self.data_dir / "feature_names.pkl"
        
        # Состояние
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.last_timestamp = None
        self.last_mtime = 0.0
        
        # Загружаем модель
        self.load_model()
        
        # Настройка логирования
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.data_dir / "ml_bridge.log", encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_model(self):
        """Загрузка обученной ML модели"""
        try:
            if (self.model_file.exists() and 
                self.scaler_file.exists() and 
                self.feature_names_file.exists()):
                
                with open(self.model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                with open(self.feature_names_file, 'rb') as f:
                    self.feature_names = pickle.load(f)
                
                print("✅ ML модель загружена успешно")
                print(f"📊 Признаков в модели: {len(self.feature_names)}")
                return True
                
        except Exception as e:
            print(f"⚠️ Ошибка загрузки модели: {e}")
        
        print("❌ ML модель не найдена. Используем простую EMA логику.")
        return False
    
    def read_latest_features(self):
        """Чтение последней строки признаков"""
        if not self.features_file.exists():
            return None
            
        try:
            # Проверяем изменение файла
            mtime = os.path.getmtime(self.features_file)
            if mtime == self.last_mtime:
                return None
            self.last_mtime = mtime
            
            # Читаем последнюю строку
            with open(self.features_file, 'r') as f:
                lines = f.readlines()
            
            if len(lines) < 2:  # header + data
                return None
                
            last_line = lines[-1].strip()
            if not last_line or ';' not in last_line:
                return None
            
            return last_line
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла: {e}")
            return None
    
    def parse_features(self, line):
        """Парсинг строки признаков"""
        try:
            parts = line.split(';')
            
            # Создаем словарь признаков
            features = {
                'timestamp': parts[0],
                'open': float(parts[1]),
                'high': float(parts[2]),
                'low': float(parts[3]),
                'close': float(parts[4]),
                'volume': float(parts[5]),
                'spread': float(parts[6]),
                'rsi': float(parts[7]),
                'macd_main': float(parts[8]),
                'macd_signal': float(parts[9]),
                'macd_histogram': float(parts[10]),
                'bb_upper': float(parts[11]),
                'bb_middle': float(parts[12]),
                'bb_lower': float(parts[13]),
                'bb_position': float(parts[14]),
                'stoch_main': float(parts[15]),
                'stoch_signal': float(parts[16]),
                'ema_9': float(parts[17]),
                'ema_21': float(parts[18]),
                'ema_50': float(parts[19]),
                'sma_200': float(parts[20]),
                'atr': float(parts[21]),
                'volatility': float(parts[22]),
                'price_change_1': float(parts[23]),
                'price_change_5': float(parts[24]),
                'price_change_15': float(parts[25]),
                'volume_ratio': float(parts[26]),
                'time_hour': int(parts[27]),
                'time_dow': int(parts[28]),
                'target': float(parts[29]) if len(parts) > 29 else 0.0
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга: {e}")
            return None
    
    def predict_ml_signal(self, features):
        """ML предсказание сигнала"""
        if not ML_AVAILABLE or self.model is None:
            # Fallback к простой EMA логике
            return self.simple_ema_signal(features)
        
        try:
            # Подготавливаем признаки для модели
            feature_vector = []
            for name in self.feature_names:
                if name in features:
                    feature_vector.append(features[name])
                else:
                    feature_vector.append(0.0)  # default value
            
            X = np.array([feature_vector])
            
            # Масштабируем
            X_scaled = self.scaler.transform(X)
            
            # Предсказываем
            prediction = self.model.predict(X_scaled)[0]
            probabilities = self.model.predict_proba(X_scaled)[0]
            confidence = probabilities.max()
            
            # Конвертируем в сигнал
            signal_map = {-1: "SELL", 0: "NONE", 1: "BUY"}
            signal = signal_map.get(prediction, "NONE")
            
            return signal, confidence
            
        except Exception as e:
            self.logger.error(f"ML предсказание не удалось: {e}")
            return self.simple_ema_signal(features)
    
    def simple_ema_signal(self, features):
        """Простая EMA логика как fallback"""
        try:
            close = features['close']
            ema = features['ema_21']
            
            if abs(close - ema) < 0.01:
                return "NONE", 0.0
            elif close > ema * 1.001:
                return "BUY", 0.7
            elif close < ema * 0.999:
                return "SELL", 0.7
            else:
                return "NONE", 0.0
                
        except:
            return "NONE", 0.0
    
    def write_prediction(self, signal, confidence, timestamp):
        """Запись ML предсказания"""
        try:
            # Простой формат для MT5
            simple_payload = f"{signal};{confidence:.3f};{timestamp}\n"
            
            # Записываем
            with open(self.predictions_file, 'w') as f:
                f.write(simple_payload)
            
            # JSON для анализа
            json_data = {
                "signal": signal,
                "confidence": confidence,
                "timestamp": timestamp,
                "model_type": "ML" if self.model else "EMA_fallback",
                "generated_at": datetime.now().isoformat()
            }
            
            json_file = self.predictions_file.with_suffix('.json')
            with open(json_file, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка записи: {e}")
            return False
    
    def run_forever(self):
        """Главный цикл ML Bridge"""
        self.logger.info("=" * 70)
        self.logger.info("🧠 ML BRIDGE для MT5 - ЗАПУЩЕН")
        self.logger.info("=" * 70)
        self.logger.info(f"Признаки: {self.features_file}")
        self.logger.info(f"Предсказания: {self.predictions_file}")
        
        model_status = "ML модель" if self.model else "EMA fallback"
        self.logger.info(f"Режим: {model_status}")
        
        try:
            while True:
                # Читаем новые признаки
                line = self.read_latest_features()
                if not line:
                    time.sleep(0.1)
                    continue
                
                # Парсим признаки
                features = self.parse_features(line)
                if not features:
                    time.sleep(0.1)
                    continue
                
                # Проверяем дубликаты
                if features['timestamp'] == self.last_timestamp:
                    time.sleep(0.1)
                    continue
                self.last_timestamp = features['timestamp']
                
                # ML предсказание
                signal, confidence = self.predict_ml_signal(features)
                
                # Вывод
                status_emoji = {"BUY": "🔵", "SELL": "🔴", "NONE": "⚪"}.get(signal, "❓")
                model_emoji = "🧠" if self.model else "📊"
                
                self.logger.info(
                    f"{model_emoji}{status_emoji} [{features['timestamp']}] "
                    f"close={features['close']:.0f} rsi={features['rsi']:.0f} "
                    f"→ {signal} (conf: {confidence:.2f})"
                )
                
                # Записываем предсказание
                if self.write_prediction(signal, confidence, features['timestamp']):
                    if signal != "NONE":
                        self.logger.info(f"✅ ML SIGNAL: {signal} (confidence: {confidence:.2f})")
                
                time.sleep(0.5)  # cooldown
                
        except KeyboardInterrupt:
            self.logger.info("🛑 ML Bridge остановлен пользователем")
        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}")

def main():
    """Точка входа"""
    bridge = MLBridge()
    bridge.run_forever()

if __name__ == "__main__":
    main()