"""
Meta-Labeling Implementation

Meta-labeling - это техника, которая использует вторичную модель для фильтрации 
сигналов первичной модели. Вместо предсказания направления движения цены,
meta-labeling предсказывает, стоит ли входить в позицию по сигналу базовой модели.

Процесс:
1. Базовая модель генерирует сигналы направления (long/short)
2. Meta-модель решает: "входить" (1) или "пропустить" (0)
3. Финальное решение = базовый сигнал * meta-сигнал

Автор: Trading System Developer
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')


class MetaLabeler:
    """
    Класс для реализации meta-labeling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация meta-labeler'а
        
        Args:
            config: Конфигурация с параметрами meta-labeling
        """
        self.config = config or self._default_config()
        self.logger = self._setup_logging()
        
        # Параметры из конфига
        self.base_model_threshold = self.config.get('base_model_threshold', 0.5)
        self.meta_features = self.config.get('meta_features', [
            'volatility_regime', 'trend_strength', 'market_microstructure'
        ])
        
        # Модели
        self.meta_model = None
        self.is_trained = False
        self.feature_importance_ = None
        
        self.logger.info(f"MetaLabeler инициализирован")
        self.logger.info(f"  Base model threshold: {self.base_model_threshold}")
        self.logger.info(f"  Meta features: {self.meta_features}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            'base_model_threshold': 0.5,
            'meta_features': [
                'volatility_regime',
                'trend_strength', 
                'market_microstructure',
                'seasonality',
                'cross_asset_correlation'
            ],
            'model_type': 'logistic_regression',
            'model_params': {
                'C': 1.0,
                'penalty': 'l2',
                'solver': 'liblinear',
                'random_state': 42
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logger = logging.getLogger('MetaLabeler')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def create_meta_features(self, 
                           data: pd.DataFrame,
                           base_predictions: pd.Series,
                           base_probabilities: pd.Series = None) -> pd.DataFrame:
        """
        Создание признаков для meta-модели
        
        Args:
            data: DataFrame с ценовыми данными и индикаторами
            base_predictions: Предсказания базовой модели
            base_probabilities: Вероятности базовой модели
            
        Returns:
            DataFrame с meta-признаками
        """
        meta_features = pd.DataFrame(index=data.index)
        
        # Базовые признаки от первичной модели
        if base_probabilities is not None:
            meta_features['base_confidence'] = np.abs(base_probabilities - 0.5)
            meta_features['base_prob'] = base_probabilities
        else:
            meta_features['base_confidence'] = 0.5  # Нейтральная уверенность
        
        # Режим волатильности
        if 'volatility_regime' in self.meta_features:
            volatility_features = self._create_volatility_features(data)
            meta_features = pd.concat([meta_features, volatility_features], axis=1)
        
        # Сила тренда
        if 'trend_strength' in self.meta_features:
            trend_features = self._create_trend_features(data)
            meta_features = pd.concat([meta_features, trend_features], axis=1)
        
        # Микроструктура рынка
        if 'market_microstructure' in self.meta_features:
            microstructure_features = self._create_microstructure_features(data)
            meta_features = pd.concat([meta_features, microstructure_features], axis=1)
        
        # Сезонность
        if 'seasonality' in self.meta_features:
            seasonality_features = self._create_seasonality_features(data)
            meta_features = pd.concat([meta_features, seasonality_features], axis=1)
        
        # Кросс-активная корреляция
        if 'cross_asset_correlation' in self.meta_features:
            correlation_features = self._create_correlation_features(data)
            meta_features = pd.concat([meta_features, correlation_features], axis=1)
        
        # Заполняем NaN значения
        meta_features = meta_features.fillna(method='ffill').fillna(0)
        
        return meta_features
    
    def _create_volatility_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Создание признаков режима волатильности"""
        features = pd.DataFrame(index=data.index)
        
        # Расчет волатильности разных периодов
        for period in [10, 20, 50]:
            vol_col = f'volatility_{period}'
            if 'close' in data.columns:
                returns = data['close'].pct_change()
                features[vol_col] = returns.rolling(period).std()
                
                # Перцентиль волатильности
                features[f'vol_percentile_{period}'] = (
                    features[vol_col].rolling(100).rank(pct=True)
                )
        
        # ATR-based волатильность
        if all(col in data.columns for col in ['high', 'low', 'close']):
            atr = self._calculate_atr(data, 14)
            features['atr'] = atr
            features['atr_percentile'] = atr.rolling(50).rank(pct=True)
            
            # Нормализованная волатильность
            features['atr_normalized'] = atr / data['close']
        
        # GARCH-подобный индикатор
        if 'close' in data.columns:
            returns = data['close'].pct_change()
            features['garch_vol'] = returns.ewm(span=20).std()
        
        return features
    
    def _create_trend_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Создание признаков силы тренда"""
        features = pd.DataFrame(index=data.index)
        
        if 'close' not in data.columns:
            return features
        
        close = data['close']
        
        # Скользящие средние разных периодов
        for period in [5, 10, 20, 50]:
            sma = close.rolling(period).mean()
            features[f'sma_{period}'] = sma
            features[f'price_vs_sma_{period}'] = close / sma - 1
        
        # ADX (Directional Movement Index)
        if all(col in data.columns for col in ['high', 'low', 'close']):
            adx = self._calculate_adx(data, 14)
            features['adx'] = adx
            features['adx_strong'] = (adx > 25).astype(int)
        
        # Momentum индикаторы
        for period in [5, 10, 20]:
            features[f'momentum_{period}'] = close / close.shift(period) - 1
        
        # Линейная регрессия slope
        for period in [10, 20]:
            features[f'lr_slope_{period}'] = close.rolling(period).apply(
                lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == period else np.nan
            )
        
        return features
    
    def _create_microstructure_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Создание признаков микроструктуры рынка"""
        features = pd.DataFrame(index=data.index)
        
        # Спред high-low
        if all(col in data.columns for col in ['high', 'low']):
            features['hl_spread'] = (data['high'] - data['low']) / data['close']
            features['hl_spread_ma'] = features['hl_spread'].rolling(20).mean()
            features['hl_spread_normalized'] = (
                features['hl_spread'] / features['hl_spread_ma'] - 1
            )
        
        # Объемные индикаторы (если доступны)
        if 'volume' in data.columns:
            volume = data['volume']
            features['volume_ma'] = volume.rolling(20).mean()
            features['volume_ratio'] = volume / features['volume_ma']
            features['volume_spike'] = (features['volume_ratio'] > 2).astype(int)
            
            # Price-Volume Trend
            if 'close' in data.columns:
                price_change = data['close'].pct_change()
                features['pvt'] = (price_change * volume).cumsum()
        
        # Imbalance индикаторы
        if all(col in data.columns for col in ['open', 'close']):
            features['body_size'] = np.abs(data['close'] - data['open']) / data['close']
            features['upper_shadow'] = (data['high'] - np.maximum(data['open'], data['close'])) / data['close']
            features['lower_shadow'] = (np.minimum(data['open'], data['close']) - data['low']) / data['close']
        
        return features
    
    def _create_seasonality_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Создание признаков сезонности"""
        features = pd.DataFrame(index=data.index)
        
        if not isinstance(data.index, pd.DatetimeIndex):
            return features
        
        # Временные признаки
        features['hour'] = data.index.hour
        features['day_of_week'] = data.index.dayofweek
        features['day_of_month'] = data.index.day
        features['month'] = data.index.month
        
        # Циклические кодирования
        features['hour_sin'] = np.sin(2 * np.pi * features['hour'] / 24)
        features['hour_cos'] = np.cos(2 * np.pi * features['hour'] / 24)
        features['dow_sin'] = np.sin(2 * np.pi * features['day_of_week'] / 7)
        features['dow_cos'] = np.cos(2 * np.pi * features['day_of_week'] / 7)
        
        # Торговые сессии
        features['asian_session'] = ((features['hour'] >= 0) & (features['hour'] < 8)).astype(int)
        features['european_session'] = ((features['hour'] >= 8) & (features['hour'] < 16)).astype(int)
        features['us_session'] = ((features['hour'] >= 16) & (features['hour'] < 24)).astype(int)
        
        return features
    
    def _create_correlation_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Создание признаков кросс-активной корреляции"""
        features = pd.DataFrame(index=data.index)
        
        # Заглушка для кросс-активных признаков
        # В реальной реализации здесь будут корреляции с другими активами
        features['cross_corr_placeholder'] = 0
        
        return features
    
    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Расчет Average True Range"""
        high_low = data['high'] - data['low']
        high_close_prev = np.abs(data['high'] - data['close'].shift(1))
        low_close_prev = np.abs(data['low'] - data['close'].shift(1))
        
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        return true_range.ewm(span=period, adjust=False).mean()
    
    def _calculate_adx(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Расчет Average Directional Index"""
        high, low, close = data['high'], data['low'], data['close']
        
        # Directional Movement
        dm_plus = np.where((high.diff() > low.diff().abs()) & (high.diff() > 0), high.diff(), 0)
        dm_minus = np.where((low.diff().abs() > high.diff()) & (low.diff() < 0), low.diff().abs(), 0)
        
        # True Range
        tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
        
        # Smoothed values
        dm_plus_smooth = pd.Series(dm_plus).ewm(span=period).mean()
        dm_minus_smooth = pd.Series(dm_minus).ewm(span=period).mean()
        tr_smooth = pd.Series(tr).ewm(span=period).mean()
        
        # Directional Indicators
        di_plus = 100 * dm_plus_smooth / tr_smooth
        di_minus = 100 * dm_minus_smooth / tr_smooth
        
        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.ewm(span=period).mean()
        
        return adx
    
    def create_meta_labels(self,
                          base_predictions: pd.Series,
                          triple_barrier_results: pd.DataFrame) -> pd.Series:
        """
        Создание меток для meta-модели
        
        Args:
            base_predictions: Предсказания базовой модели (направление)
            triple_barrier_results: Результаты triple-barrier labeling
            
        Returns:
            Series с meta-метками (1 = входить, 0 = пропустить)
        """
        meta_labels = pd.Series(0, index=base_predictions.index)
        
        # Для каждого сигнала базовой модели определяем, был ли он прибыльным
        for _, trade in triple_barrier_results.iterrows():
            entry_time = trade['entry_time']
            
            if entry_time in base_predictions.index:
                # Если сделка была прибыльной, помечаем как "входить" (1)
                if trade['return'] > 0:
                    meta_labels[entry_time] = 1
                else:
                    meta_labels[entry_time] = 0
        
        return meta_labels
    
    def train(self,
             meta_features: pd.DataFrame,
             meta_labels: pd.Series,
             validation_split: float = 0.2) -> Dict[str, Any]:
        """
        Обучение meta-модели
        
        Args:
            meta_features: Признаки для meta-модели
            meta_labels: Метки (1 = входить, 0 = пропустить)
            validation_split: Доля данных для валидации
            
        Returns:
            Dict с результатами обучения
        """
        self.logger.info("Начинаем обучение meta-модели")
        
        # Подготовка данных
        X = meta_features.dropna()
        y = meta_labels.loc[X.index]
        
        if len(X) == 0:
            raise ValueError("Нет данных для обучения meta-модели")
        
        self.logger.info(f"Данные для обучения: {len(X)} образцов, {X.shape[1]} признаков")
        self.logger.info(f"Распределение меток: {y.value_counts().to_dict()}")
        
        # Создание модели
        model_type = self.config.get('model_type', 'logistic_regression')
        model_params = self.config.get('model_params', {})
        
        if model_type == 'logistic_regression':
            self.meta_model = LogisticRegression(**model_params)
        elif model_type == 'random_forest':
            self.meta_model = RandomForestClassifier(**model_params)
        else:
            raise ValueError(f"Неподдерживаемый тип модели: {model_type}")
        
        # Обучение
        self.meta_model.fit(X, y)
        
        # Валидация
        cv_scores = cross_val_score(self.meta_model, X, y, cv=5, scoring='accuracy')
        
        # Предсказания на обучающих данных
        y_pred = self.meta_model.predict(X)
        accuracy = accuracy_score(y, y_pred)
        
        # Важность признаков
        if hasattr(self.meta_model, 'feature_importances_'):
            self.feature_importance_ = dict(zip(X.columns, self.meta_model.feature_importances_))
        elif hasattr(self.meta_model, 'coef_'):
            self.feature_importance_ = dict(zip(X.columns, np.abs(self.meta_model.coef_[0])))
        
        self.is_trained = True
        
        results = {
            'accuracy': accuracy,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'n_samples': len(X),
            'n_features': X.shape[1],
            'feature_importance': self.feature_importance_
        }
        
        self.logger.info(f"Meta-модель обучена:")
        self.logger.info(f"  Точность: {accuracy:.3f}")
        self.logger.info(f"  CV точность: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        
        return results
    
    def predict(self, meta_features: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Предсказание meta-модели
        
        Args:
            meta_features: Признаки для предсказания
            
        Returns:
            Tuple (predictions, probabilities)
        """
        if not self.is_trained or self.meta_model is None:
            raise ValueError("Meta-модель не обучена")
        
        X = meta_features.fillna(method='ffill').fillna(0)
        
        predictions = pd.Series(
            self.meta_model.predict(X), 
            index=X.index
        )
        
        probabilities = pd.Series(
            self.meta_model.predict_proba(X)[:, 1],
            index=X.index
        )
        
        return predictions, probabilities
    
    def apply_meta_filter(self,
                         base_signals: pd.Series,
                         meta_predictions: pd.Series,
                         confidence_threshold: float = 0.5) -> pd.Series:
        """
        Применение meta-фильтра к базовым сигналам
        
        Args:
            base_signals: Базовые торговые сигналы
            meta_predictions: Предсказания meta-модели
            confidence_threshold: Порог уверенности
            
        Returns:
            Отфильтрованные сигналы
        """
        # Применяем фильтр только там, где есть базовые сигналы
        filtered_signals = base_signals.copy()
        
        for idx in base_signals.index:
            if base_signals[idx] != 0 and idx in meta_predictions.index:
                # Если meta-модель говорит "не входить", обнуляем сигнал
                if meta_predictions[idx] < confidence_threshold:
                    filtered_signals[idx] = 0
        
        reduction_rate = (base_signals != 0).sum() - (filtered_signals != 0).sum()
        self.logger.info(f"Meta-фильтр исключил {reduction_rate} сигналов")
        
        return filtered_signals
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Получение важности признаков"""
        if not self.feature_importance_:
            return {}
        
        return dict(sorted(
            self.feature_importance_.items(),
            key=lambda x: x[1],
            reverse=True
        ))


def create_sample_meta_data():
    """Создание примера данных для тестирования meta-labeling"""
    np.random.seed(42)
    
    # Генерируем синтетические данные
    n_bars = 1000
    dates = pd.date_range(start='2023-01-01', periods=n_bars, freq='15min')
    
    # OHLC данные
    price_changes = np.random.normal(0, 0.001, n_bars)
    close_prices = 100 * np.exp(np.cumsum(price_changes))
    
    data = pd.DataFrame({
        'datetime': dates,
        'open': close_prices + np.random.normal(0, 0.001, n_bars),
        'high': close_prices + np.abs(np.random.normal(0, 0.002, n_bars)),
        'low': close_prices - np.abs(np.random.normal(0, 0.002, n_bars)),
        'close': close_prices,
        'volume': np.random.lognormal(10, 1, n_bars)
    })
    
    data.set_index('datetime', inplace=True)
    
    # Базовые предсказания (случайные сигналы)
    base_predictions = pd.Series(0, index=data.index)
    signal_indices = np.random.choice(data.index[50:-50], size=50, replace=False)
    for idx in signal_indices:
        base_predictions[idx] = np.random.choice([-1, 1])
    
    # Создаем синтетические результаты triple-barrier
    triple_barrier_results = []
    for idx in signal_indices:
        # Случайная прибыльность с небольшим bias
        return_val = np.random.normal(0.001, 0.01)  # Небольшой положительный bias
        
        triple_barrier_results.append({
            'entry_time': idx,
            'entry_price': data.loc[idx, 'close'],
            'return': return_val,
            'label': 1 if return_val > 0 else -1
        })
    
    triple_barrier_results = pd.DataFrame(triple_barrier_results)
    
    return data, base_predictions, triple_barrier_results


if __name__ == "__main__":
    # Пример использования
    print("Тестирование Meta-Labeler...")
    
    # Создаем тестовые данные
    data, base_predictions, triple_barrier_results = create_sample_meta_data()
    print(f"Создано {len(data)} баров данных")
    print(f"Базовых сигналов: {(base_predictions != 0).sum()}")
    print(f"Triple barrier результатов: {len(triple_barrier_results)}")
    
    # Создаем meta-labeler
    config = {
        'meta_features': ['volatility_regime', 'trend_strength', 'seasonality'],
        'model_type': 'logistic_regression'
    }
    
    meta_labeler = MetaLabeler(config)
    
    # Создаем meta-признаки
    meta_features = meta_labeler.create_meta_features(data, base_predictions)
    print(f"Создано {meta_features.shape[1]} meta-признаков")
    
    # Создаем meta-метки
    meta_labels = meta_labeler.create_meta_labels(base_predictions, triple_barrier_results)
    print(f"Meta-меток: {meta_labels.sum()} из {len(meta_labels[meta_labels.index.isin(base_predictions[base_predictions != 0].index)])}")
    
    # Обучаем meta-модель
    if meta_labels.sum() > 0:
        training_results = meta_labeler.train(meta_features, meta_labels)
        print(f"\nРезультаты обучения:")
        for key, value in training_results.items():
            if key != 'feature_importance':
                print(f"  {key}: {value}")
        
        # Применяем meta-фильтр
        meta_pred, meta_prob = meta_labeler.predict(meta_features)
        filtered_signals = meta_labeler.apply_meta_filter(base_predictions, meta_prob, 0.5)
        
        original_signals = (base_predictions != 0).sum()
        filtered_signals_count = (filtered_signals != 0).sum()
        
        print(f"\nФильтрация сигналов:")
        print(f"  Оригинальных сигналов: {original_signals}")
        print(f"  После фильтрации: {filtered_signals_count}")
        print(f"  Исключено: {original_signals - filtered_signals_count} ({100*(original_signals - filtered_signals_count)/original_signals:.1f}%)")
        
        # Важность признаков
        importance = meta_labeler.get_feature_importance()
        print(f"\nТоп-5 важных признаков:")
        for i, (feature, imp) in enumerate(list(importance.items())[:5]):
            print(f"  {i+1}. {feature}: {imp:.4f}")
    
    else:
        print("Недостаточно положительных меток для обучения")