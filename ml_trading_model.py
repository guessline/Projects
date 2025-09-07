"""
ML модель для предсказания торговых сигналов
Использует Random Forest для классификации сигналов BUY/SELL/HOLD
"""

import os
import json
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')


class TradingMLModel:
    def __init__(self, config_path='config.json'):
        """Инициализация ML модели"""
        self.config = self._load_config(config_path)
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.is_trained = False
        self.last_retrain = None
        self.training_data = []
        
        # Настройка логирования
        self._setup_logging()
        
    def _load_config(self, config_path):
        """Загрузка конфигурации"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return self._default_config()
    
    def _default_config(self):
        """Конфигурация по умолчанию"""
        return {
            "ml_model": {
                "lookback_periods": 20,
                "features": ["close", "ema", "atr", "price_change", "ema_diff", "volatility"],
                "retrain_interval_hours": 24,
                "min_training_samples": 100
            },
            "trading": {
                "ml_confidence_threshold": 0.7
            }
        }
    
    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger('TradingML')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def create_features(self, data):
        """Создание признаков для ML модели"""
        df = data.copy()
        
        # Базовые признаки
        df['price_change'] = df['close'].pct_change()
        df['ema_diff'] = (df['close'] - df['ema']) / df['ema']
        df['volatility'] = df['close'].rolling(window=5).std()
        
        # Технические индикаторы
        df['rsi'] = self._calculate_rsi(df['close'])
        df['bb_upper'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Скользящие средние разных периодов
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['ema_5'] = df['close'].ewm(span=5).mean()
        df['ema_10'] = df['close'].ewm(span=10).mean()
        
        # Относительные признаки
        df['close_to_sma5'] = df['close'] / df['sma_5'] - 1
        df['close_to_sma10'] = df['close'] / df['sma_10'] - 1
        df['ema_5_to_10'] = df['ema_5'] / df['ema_10'] - 1
        
        # Объемные признаки (если доступны)
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(window=10).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Лаговые признаки
        for lag in [1, 2, 3, 5]:
            df[f'price_change_lag_{lag}'] = df['price_change'].shift(lag)
            df[f'ema_diff_lag_{lag}'] = df['ema_diff'].shift(lag)
        
        return df
    
    def _calculate_rsi(self, prices, period=14):
        """Расчет RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Расчет полос Боллинджера"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band
    
    def create_labels(self, data, future_periods=5):
        """Создание меток для обучения"""
        df = data.copy()
        
        # Прогнозируем движение цены на future_periods вперед
        future_price = df['close'].shift(-future_periods)
        current_price = df['close']
        
        # Рассчитываем процентное изменение
        price_change_pct = (future_price - current_price) / current_price * 100
        
        # Создаем метки
        labels = []
        for change in price_change_pct:
            if pd.isna(change):
                labels.append('HOLD')
            elif change > 0.5:  # Рост больше 0.5%
                labels.append('BUY')
            elif change < -0.5:  # Падение больше 0.5%
                labels.append('SELL')
            else:
                labels.append('HOLD')
        
        return pd.Series(labels, index=df.index)
    
    def prepare_training_data(self, data):
        """Подготовка данных для обучения"""
        # Создаем признаки
        df_features = self.create_features(data)
        
        # Создаем метки
        labels = self.create_labels(data)
        df_features['target'] = labels
        
        # Убираем NaN значения
        df_features = df_features.dropna()
        
        # Выбираем признаки для модели
        feature_cols = [col for col in df_features.columns 
                       if col not in ['target', 'timestamp'] and not col.startswith('bb_')]
        
        X = df_features[feature_cols]
        y = df_features['target']
        
        self.feature_columns = feature_cols
        self.logger.info(f"Подготовлено {len(X)} образцов с {len(feature_cols)} признаками")
        
        return X, y
    
    def train_model(self, X, y):
        """Обучение модели"""
        try:
            # Разделяем данные
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Масштабируем признаки
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Создаем и обучаем модель
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Оценка модели
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.logger.info(f"Модель обучена с точностью: {accuracy:.3f}")
            self.logger.info("Отчет по классификации:")
            self.logger.info("\n" + classification_report(y_test, y_pred))
            
            self.is_trained = True
            self.last_retrain = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обучения модели: {e}")
            return False
    
    def predict_signal(self, current_data):
        """Предсказание торгового сигнала"""
        if not self.is_trained or self.model is None:
            return "HOLD", 0.0
        
        try:
            # Создаем признаки для текущих данных
            df_features = self.create_features(current_data)
            
            # Берем последнюю строку (текущие данные)
            latest_features = df_features[self.feature_columns].iloc[-1:].values
            
            # Проверяем на NaN
            if np.any(np.isnan(latest_features)):
                self.logger.warning("Обнаружены NaN в признаках, возвращаем HOLD")
                return "HOLD", 0.0
            
            # Масштабируем признаки
            features_scaled = self.scaler.transform(latest_features)
            
            # Получаем предсказание и вероятности
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Находим максимальную вероятность
            max_prob = max(probabilities)
            
            # Проверяем порог уверенности
            confidence_threshold = self.config['trading']['ml_confidence_threshold']
            if max_prob < confidence_threshold:
                return "HOLD", max_prob
            
            return prediction, max_prob
            
        except Exception as e:
            self.logger.error(f"Ошибка предсказания: {e}")
            return "HOLD", 0.0
    
    def save_model(self, filepath):
        """Сохранение модели"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'is_trained': self.is_trained,
                'last_retrain': self.last_retrain,
                'config': self.config
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info(f"Модель сохранена: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения модели: {e}")
            return False
    
    def load_model(self, filepath):
        """Загрузка модели"""
        try:
            if not os.path.exists(filepath):
                self.logger.warning(f"Файл модели не найден: {filepath}")
                return False
            
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.is_trained = model_data['is_trained']
            self.last_retrain = model_data.get('last_retrain')
            
            self.logger.info(f"Модель загружена: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки модели: {e}")
            return False
    
    def should_retrain(self):
        """Проверка необходимости переобучения"""
        if not self.last_retrain:
            return True
        
        retrain_interval = self.config['ml_model']['retrain_interval_hours']
        time_since_retrain = datetime.now() - self.last_retrain
        
        return time_since_retrain.total_seconds() > retrain_interval * 3600
    
    def get_feature_importance(self):
        """Получение важности признаков"""
        if not self.is_trained or self.model is None:
            return {}
        
        try:
            importance = self.model.feature_importances_
            feature_importance = dict(zip(self.feature_columns, importance))
            
            # Сортируем по важности
            sorted_importance = dict(sorted(
                feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            ))
            
            return sorted_importance
            
        except Exception as e:
            self.logger.error(f"Ошибка получения важности признаков: {e}")
            return {}


def create_sample_data():
    """Создание примера данных для тестирования"""
    np.random.seed(42)
    
    # Генерируем синтетические данные
    n_samples = 1000
    dates = pd.date_range(start='2023-01-01', periods=n_samples, freq='1H')
    
    # Случайное блуждание для цены
    price_changes = np.random.normal(0, 0.001, n_samples)
    prices = 100 * np.exp(np.cumsum(price_changes))
    
    # EMA
    ema = pd.Series(prices).ewm(span=20).mean()
    
    # ATR (упрощенный)
    high = prices * (1 + np.abs(np.random.normal(0, 0.005, n_samples)))
    low = prices * (1 - np.abs(np.random.normal(0, 0.005, n_samples)))
    atr = pd.Series(high - low).rolling(window=14).mean()
    
    data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'ema': ema,
        'atr': atr.fillna(atr.mean())
    })
    
    return data


if __name__ == "__main__":
    # Пример использования
    print("Тестирование ML модели для торговых сигналов...")
    
    # Создаем модель
    ml_model = TradingMLModel()
    
    # Создаем тестовые данные
    sample_data = create_sample_data()
    print(f"Создано {len(sample_data)} образцов данных")
    
    # Подготавливаем данные для обучения
    X, y = ml_model.prepare_training_data(sample_data)
    print(f"Распределение меток: {y.value_counts().to_dict()}")
    
    # Обучаем модель
    if ml_model.train_model(X, y):
        print("Модель успешно обучена!")
        
        # Сохраняем модель
        ml_model.save_model('ml_model.pkl')
        
        # Тестируем предсказание
        test_data = sample_data.tail(50)  # Последние 50 записей
        signal, confidence = ml_model.predict_signal(test_data)
        print(f"Предсказанный сигнал: {signal} (уверенность: {confidence:.3f})")
        
        # Показываем важность признаков
        importance = ml_model.get_feature_importance()
        print("\nВажность признаков (топ-10):")
        for i, (feature, imp) in enumerate(list(importance.items())[:10]):
            print(f"{i+1}. {feature}: {imp:.4f}")
    
    else:
        print("Ошибка обучения модели!")