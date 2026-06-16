#!/usr/bin/env python3
"""
ML Trainer для MT5 Trading System

Обучение модели машинного обучения на исторических данных MT5.
Создает обученную модель для предсказания движения цен.
"""

import os
import sys
import pickle
import warnings
from datetime import datetime
from pathlib import Path

# Подавляем предупреждения
warnings.filterwarnings('ignore')

# Проверяем наличие ML библиотек
try:
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
    ML_AVAILABLE = True
    print("✅ ML библиотеки доступны")
except ImportError as e:
    print("❌ ML библиотеки не установлены!")
    print("Установите: pip install pandas numpy scikit-learn")
    ML_AVAILABLE = False

class MLTrainer:
    """Тренер ML модели для торговли"""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            self.data_dir = Path(r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
        else:
            self.data_dir = Path(data_dir)
            
        self.features_file = self.data_dir / "ml_features.csv"
        self.model_file = self.data_dir / "trading_model.pkl"
        self.scaler_file = self.data_dir / "feature_scaler.pkl"
        self.feature_names_file = self.data_dir / "feature_names.pkl"
        
    def load_data(self):
        """Загрузка данных из CSV файла"""
        if not self.features_file.exists():
            print(f"❌ Файл данных не найден: {self.features_file}")
            return None
            
        try:
            # Загружаем CSV с правильными типами
            df = pd.read_csv(self.features_file, sep=';')
            print(f"✅ Загружено {len(df)} записей из {self.features_file}")
            print(f"📊 Столбцы: {list(df.columns)}")
            
            # Базовая очистка данных
            df = df.dropna()
            df = df[df['close'] > 0]
            df = df[df['volume'] > 0]
            
            print(f"✅ После очистки: {len(df)} записей")
            return df
            
        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
            return None
    
    def prepare_features(self, df):
        """Подготовка признаков для ML"""
        print("🔧 Подготовка признаков...")
        
        # Создаем дополнительные признаки
        df = df.copy()
        
        # Технические соотношения
        df['close_ema21_ratio'] = df['close'] / df['ema_21']
        df['ema9_ema21_ratio'] = df['ema_9'] / df['ema_21']
        df['price_bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Моментум индикаторы
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['macd_bullish'] = (df['macd_main'] > df['macd_signal']).astype(int)
        
        # Волатильность
        df['atr_normalized'] = df['atr'] / df['close']
        df['volatility_high'] = (df['volatility'] > df['volatility'].quantile(0.8)).astype(int)
        
        # Временные признаки
        df['is_london_session'] = ((df['time_hour'] >= 8) & (df['time_hour'] <= 17)).astype(int)
        df['is_ny_session'] = ((df['time_hour'] >= 13) & (df['time_hour'] <= 22)).astype(int)
        df['is_weekend'] = (df['time_dow'].isin([0, 6])).astype(int)
        
        # Выбираем признаки для модели
        feature_columns = [
            'rsi', 'macd_main', 'macd_signal', 'macd_histogram',
            'bb_position', 'stoch_main', 'stoch_signal',
            'price_change_1', 'price_change_5', 'price_change_15',
            'volume_ratio', 'atr_normalized', 'volatility',
            'close_ema21_ratio', 'ema9_ema21_ratio', 'price_bb_position',
            'rsi_overbought', 'rsi_oversold', 'macd_bullish',
            'volatility_high', 'is_london_session', 'is_ny_session'
        ]
        
        # Проверяем наличие всех столбцов
        available_features = [col for col in feature_columns if col in df.columns]
        missing_features = [col for col in feature_columns if col not in df.columns]
        
        if missing_features:
            print(f"⚠️ Отсутствующие признаки: {missing_features}")
        
        print(f"✅ Используем {len(available_features)} признаков")
        
        X = df[available_features].values
        
        # Создаем целевую переменную из target
        y = np.where(df['target'] > 0.0001, 1,      # BUY если рост > 0.01%
                    np.where(df['target'] < -0.0001, -1, 0))  # SELL если падение > 0.01%, иначе NONE
        
        print(f"📊 Распределение классов:")
        unique, counts = np.unique(y, return_counts=True)
        for label, count in zip(unique, counts):
            label_name = {-1: "SELL", 0: "NONE", 1: "BUY"}.get(label, str(label))
            print(f"   {label_name}: {count} ({count/len(y)*100:.1f}%)")
        
        return X, y, available_features
    
    def train_model(self, X, y, feature_names):
        """Обучение ML модели"""
        print("🧠 Обучение ML модели...")
        
        # Разделение данных
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"📊 Обучающая выборка: {len(X_train)}")
        print(f"📊 Тестовая выборка: {len(X_test)}")
        
        # Масштабирование признаков
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Обучение модели
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        
        print("🔄 Обучение Random Forest...")
        model.fit(X_train_scaled, y_train)
        
        # Оценка модели
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ Точность модели: {accuracy:.3f}")
        
        # Кросс-валидация
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
        print(f"📊 Кросс-валидация: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        # Важность признаков
        feature_importance = dict(zip(feature_names, model.feature_importances_))
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
        
        print(f"\n🏆 Топ-10 важных признаков:")
        for name, importance in top_features:
            print(f"   {name}: {importance:.3f}")
        
        # Детальный отчет
        print(f"\n📋 Детальная оценка:")
        print(classification_report(y_test, y_pred, 
                                  target_names=['SELL', 'NONE', 'BUY']))
        
        return model, scaler, accuracy
    
    def save_model(self, model, scaler, feature_names):
        """Сохранение обученной модели"""
        try:
            with open(self.model_file, 'wb') as f:
                pickle.dump(model, f)
            with open(self.scaler_file, 'wb') as f:
                pickle.dump(scaler, f)
            with open(self.feature_names_file, 'wb') as f:
                pickle.dump(feature_names, f)
                
            print(f"✅ Модель сохранена:")
            print(f"   Модель: {self.model_file}")
            print(f"   Скейлер: {self.scaler_file}")
            print(f"   Признаки: {self.feature_names_file}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    
    def create_sample_data(self):
        """Создание примера данных для тестирования"""
        print("📊 Создание примера ML данных...")
        
        # Создаем синтетические данные
        np.random.seed(42)
        n_samples = 1000
        
        # Базовые цены
        base_price = 1.0850
        prices = []
        current_price = base_price
        
        for i in range(n_samples):
            # Случайное движение с трендом
            trend = 0.00001 if i < 500 else -0.00001
            noise = np.random.normal(0, 0.00005)
            current_price += trend + noise
            prices.append(current_price)
        
        # Создаем DataFrame
        data = []
        for i in range(50, n_samples):  # начинаем с 50 для расчета индикаторов
            timestamp = datetime.now() - timedelta(minutes=(n_samples-i)*5)
            
            # OHLCV (упрощенно)
            close = prices[i]
            open_price = prices[i-1] + np.random.normal(0, 0.00002)
            high = max(open_price, close) + abs(np.random.normal(0, 0.00003))
            low = min(open_price, close) - abs(np.random.normal(0, 0.00003))
            volume = np.random.randint(100, 1000)
            spread = np.random.uniform(1, 3)
            
            # Технические индикаторы (упрощенно)
            rsi = 30 + (i % 40) + np.random.normal(0, 5)
            
            # EMA
            ema_21 = np.mean(prices[i-20:i+1])
            ema_9 = np.mean(prices[i-8:i+1])
            ema_50 = np.mean(prices[i-49:i+1]) if i >= 49 else ema_21
            sma_200 = np.mean(prices[max(0,i-199):i+1])
            
            # MACD (упрощенно)
            macd_main = ema_9 - ema_21
            macd_signal = macd_main * 0.8
            macd_histogram = macd_main - macd_signal
            
            # Bollinger Bands
            bb_middle = ema_21
            bb_std = np.std(prices[i-19:i+1])
            bb_upper = bb_middle + 2 * bb_std
            bb_lower = bb_middle - 2 * bb_std
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            
            # Stochastic (упрощенно)
            stoch_main = ((close - low) / (high - low)) * 100 if high != low else 50
            stoch_signal = stoch_main * 0.9
            
            # ATR
            atr = (high - low + abs(high - prices[i-1]) + abs(low - prices[i-1])) / 3
            volatility = (high - low) / close
            
            # Price changes
            price_change_1 = (close - prices[i-1]) / prices[i-1]
            price_change_5 = (close - prices[i-5]) / prices[i-5] if i >= 5 else 0
            price_change_15 = (close - prices[i-15]) / prices[i-15] if i >= 15 else 0
            
            # Volume ratio
            volume_ratio = volume / np.mean([100, 200, 300, 400, 500])  # упрощенно
            
            # Time features
            time_hour = timestamp.hour
            time_dow = timestamp.weekday()
            
            # Target (будущее движение)
            if i < len(prices) - 1:
                target = (prices[i+1] - close) / close
            else:
                target = 0
            
            data.append({
                'timestamp': timestamp.strftime('%Y.%m.%d %H:%M'),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'spread': spread,
                'rsi': rsi,
                'macd_main': macd_main,
                'macd_signal': macd_signal,
                'macd_histogram': macd_histogram,
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'bb_position': bb_position,
                'stoch_main': stoch_main,
                'stoch_signal': stoch_signal,
                'ema_9': ema_9,
                'ema_21': ema_21,
                'ema_50': ema_50,
                'sma_200': sma_200,
                'atr': atr,
                'volatility': volatility,
                'price_change_1': price_change_1,
                'price_change_5': price_change_5,
                'price_change_15': price_change_15,
                'volume_ratio': volume_ratio,
                'time_hour': time_hour,
                'time_dow': time_dow,
                'target': target
            })
        
        df = pd.DataFrame(data)
        
        # Сохраняем пример данных
        sample_file = self.data_dir / "sample_ml_features.csv"
        df.to_csv(sample_file, sep=';', index=False)
        print(f"✅ Пример данных сохранен: {sample_file}")
        
        return df
    
    def prepare_ml_data(self, df):
        """Подготовка данных для ML"""
        print("🔧 Подготовка данных для ML...")
        
        # Выбираем признаки (исключаем timestamp и target)
        feature_columns = [col for col in df.columns if col not in ['timestamp', 'target']]
        
        X = df[feature_columns].values
        
        # Создаем классы для предсказания
        # Классифицируем изменения цены
        y = np.where(df['target'] > 0.0001, 1,          # BUY если рост > 0.01%
                    np.where(df['target'] < -0.0001, -1, 0))  # SELL если падение > 0.01%
        
        print(f"📊 Признаков: {X.shape[1]}")
        print(f"📊 Образцов: {X.shape[0]}")
        
        # Статистика классов
        unique, counts = np.unique(y, return_counts=True)
        for label, count in zip(unique, counts):
            label_name = {-1: "SELL", 0: "NONE", 1: "BUY"}.get(label, str(label))
            print(f"   {label_name}: {count} ({count/len(y)*100:.1f}%)")
        
        return X, y, feature_columns
    
    def train_and_evaluate(self, X, y, feature_names):
        """Обучение и оценка модели"""
        print("🧠 Обучение модели...")
        
        # Разделение данных
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Масштабирование
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Обучение Random Forest
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'  # балансируем классы
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Оценка
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ Точность: {accuracy:.3f}")
        
        # Кросс-валидация
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
        print(f"📊 Кросс-валидация: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        # Важность признаков
        feature_importance = list(zip(feature_names, model.feature_importances_))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n🏆 Топ-10 важных признаков:")
        for name, importance in feature_importance[:10]:
            print(f"   {name}: {importance:.3f}")
        
        # Детальный отчет
        print(f"\n📋 Классификационный отчет:")
        print(classification_report(y_test, y_pred, 
                                  target_names=['SELL', 'NONE', 'BUY']))
        
        return model, scaler, accuracy

def main():
    """Главная функция обучения"""
    print("🧠 ML TRAINER для MT5 Trading System")
    print("="*60)
    
    if not ML_AVAILABLE:
        print("❌ Установите ML библиотеки:")
        print("pip install pandas numpy scikit-learn")
        return
    
    # Создаем тренер
    trainer = MLTrainer()
    
    # Загружаем или создаем данные
    df = trainer.load_data()
    
    if df is None or len(df) < 100:
        print("📊 Создаем пример данных для демонстрации...")
        df = trainer.create_sample_data()
    
    if df is None:
        print("❌ Не удалось получить данные")
        return
    
    # Подготавливаем данные
    X, y, feature_names = trainer.prepare_ml_data(df)
    
    if len(np.unique(y)) < 2:
        print("❌ Недостаточно разнообразия в данных для обучения")
        return
    
    # Обучаем модель
    model, scaler, accuracy = trainer.train_and_evaluate(X, y, feature_names)
    
    # Сохраняем модель
    trainer.save_model(model, scaler, feature_names)
    
    print(f"\n🎉 ОБУЧЕНИЕ ЗАВЕРШЕНО!")
    print(f"✅ Модель готова к использованию")
    print(f"📊 Итоговая точность: {accuracy:.1%}")
    
    if accuracy > 0.6:
        print("🎯 Модель показывает хорошие результаты!")
    else:
        print("⚠️ Модель требует улучшения (больше данных/признаков)")
    
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()