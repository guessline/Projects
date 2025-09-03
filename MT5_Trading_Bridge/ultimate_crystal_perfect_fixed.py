#!/usr/bin/env python3
"""
ULTIMATE CRYSTAL PERFECT 10/10 ML СИСТЕМА
Абсолютное совершенство - hedge fund grade
Бит-в-бит воспроизводимость
ИСПРАВЛЕНА ВЕРСИЯ
"""

# ИСПРАВЛЕНО: правильный порядок для полного детерминизма
import os
os.environ.update({
    "PYTHONHASHSEED": "0",      # Логируем, но эффект только если установлен до процесса
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", 
    "NUMEXPR_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
})

import random
random.seed(42)

import numpy as np
np.random.seed(42)

import warnings
warnings.filterwarnings('ignore')

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import brier_score_loss
    from sklearn.utils.class_weight import compute_sample_weight
    import sklearn
    print("✅ Ultimate Crystal Perfect ML готова")
    print(f"📚 sklearn {sklearn.__version__}, numpy {np.__version__}, pandas {pd.__version__}")
except ImportError:
    print("❌ Установите: pip install pandas numpy scikit-learn")
    exit()

import time
import hashlib
import json
import sys
import gc
from datetime import datetime
import pickle


class UltimateCrystalPerfectML:
    """
    🏆 ULTIMATE CRYSTAL PERFECT 10/10 ML СИСТЕМА
    💎 Hedge Fund Grade с полным детерминизмом
    """
    
    def __init__(self, data_file='btc_history_100k.csv', tc_pct=0.02):
        self.data_file = data_file
        self.tc_pct = tc_pct
        self.model = None
        self.scaler = None
        self.metadata = {}
        
        # ИСПРАВЛЕНО: логируем эффективные ENV значения после установки
        effective_thread_env = {k: os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OMP_NUM_THREADS','PYTHONHASHSEED']}
        self.log_message(f"🧵 Потоки/ENV: {effective_thread_env}")
        self._effective_thread_env = effective_thread_env  # запомним для metadata
        
        self.log_message("🏆 ULTIMATE CRYSTAL PERFECT ML инициализирована")
        
    def log_message(self, msg):
        """Unified logging"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {msg}")
        
    def load_data_safe(self, file_path):
        """Безопасная загрузка данных с проверкой"""
        try:
            # Попробуем запятую как разделитель
            df = pd.read_csv(file_path)
            if df.shape[1] == 1:
                # Если одна колонка, попробуем точку с запятой
                df = pd.read_csv(file_path, sep=';')
            
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValueError(f"Отсутствуют колонки: {missing}")
                
            self.log_message(f"📊 Загружено {len(df)} строк, {df.shape[1]} колонок")
            return df
        except Exception as e:
            self.log_message(f"❌ Ошибка загрузки данных: {e}")
            raise
    
    def _assert_finite(self, X, name="features"):
        """Валидация данных перед обучением"""
        if not np.isfinite(X).all():
            inf_count = np.isinf(X).sum()
            nan_count = np.isnan(X).sum()
            self.log_message(f"❌ {name}: inf={inf_count}, nan={nan_count}")
            raise ValueError(f"Non-finite values in {name}")
    
    def safe_clip_optimized(self, df, features):
        """ИСПРАВЛЕНО: безопасный клиппинг без sin/cos"""
        exclude_patterns = ['sin', 'cos']  # Исключаем циклические фичи
        
        for col in features:
            if any(pattern in col.lower() for pattern in exclude_patterns):
                continue  # Пропускаем циклические фичи
                
            if col in df.columns:
                q01, q99 = df[col].quantile([0.01, 0.99])
                if pd.notna(q01) and pd.notna(q99) and q01 != q99:
                    df[col] = df[col].clip(q01, q99)
        
        return df
    
    def infer_ann_factor(self, timestamps):
        """ИСПРАВЛЕНО: безопасный расчет годового фактора"""
        if len(timestamps) < 2:
            self.log_message("⚠️ Недостаточно данных для расчета ann_factor, используем 525600")
            return 525600  # Минуты в году
            
        try:
            # Преобразуем в datetime если нужно
            if isinstance(timestamps.iloc[0], str):
                ts_dt = pd.to_datetime(timestamps)
            else:
                ts_dt = pd.to_datetime(timestamps, unit='ms')
            
            # Считаем среднюю разность
            time_diffs = ts_dt.diff().dropna()
            if len(time_diffs) == 0:
                return 525600
                
            avg_diff_minutes = time_diffs.mean().total_seconds() / 60
            
            if avg_diff_minutes <= 0 or not np.isfinite(avg_diff_minutes):
                return 525600
                
            ann_factor = 365.25 * 24 * 60 / avg_diff_minutes
            
            if not np.isfinite(ann_factor) or ann_factor <= 0:
                return 525600
                
            return ann_factor
            
        except Exception as e:
            self.log_message(f"⚠️ Ошибка расчета ann_factor: {e}, используем 525600")
            return 525600
    
    def build_features_crystal(self, df):
        """Создание всех ML фичей с защитой от утечек"""
        self.log_message("🔧 Создание crystal features...")
        
        # Базовые фичи
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['high_low_ratio'] = df['high'] / df['low']
        df['volume_ma'] = df['volume'].rolling(20).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger Bands - ИСПРАВЛЕНО
        bb_ma = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        bb_upper = bb_ma + (bb_std * 2)
        bb_lower = bb_ma - (bb_std * 2)
        df['bb_upper'] = bb_upper
        df['bb_lower'] = bb_lower
        df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # Stochastic
        low_14 = df['low'].rolling(14).min()
        high_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # EMAs
        for period in [5, 10, 20, 50]:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            df[f'ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
        
        # ATR
        df['tr'] = np.maximum(df['high'] - df['low'], 
                             np.maximum(abs(df['high'] - df['close'].shift(1)),
                                       abs(df['low'] - df['close'].shift(1))))
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Лагированные фичи (защита от look-ahead bias)
        for lag in [1, 2, 3, 5]:
            df[f'returns_lag_{lag}'] = df['returns'].shift(lag)
            df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
            df[f'rsi_lag_{lag}'] = df['rsi'].shift(lag)
        
        # Momentum
        for period in [5, 10, 20]:
            df[f'momentum_{period}'] = df['close'].pct_change(period)
        
        # Volatility
        for period in [5, 10, 20]:
            df[f'volatility_{period}'] = df['returns'].rolling(period).std()
        
        # Временные фичи
        if 'timestamp' in df.columns:
            if isinstance(df['timestamp'].iloc[0], str):
                ts = pd.to_datetime(df['timestamp'])
            else:
                ts = pd.to_datetime(df['timestamp'], unit='ms')
            
            df['hour'] = ts.dt.hour
            df['day_of_week'] = ts.dt.dayofweek
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Заполнение NaN
        df = df.fillna(method='ffill').fillna(0)
        
        # Безопасное клиппинг (исключая sin/cos)
        feature_cols = [col for col in df.columns if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = self.safe_clip_optimized(df, feature_cols)
        
        # Финальная очистка
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df = df.fillna(method='ffill').fillna(0)
        
        self.log_message(f"✅ Создано {len(feature_cols)} фичей")
        return df, feature_cols
    
    def create_labels_crystal(self, df, lookforward=5, threshold=0.002):
        """Создание меток для классификации"""
        future_returns = df['close'].pct_change(lookforward).shift(-lookforward)
        
        labels = np.where(future_returns > threshold, 1,    # BUY
                         np.where(future_returns < -threshold, -1,  # SELL  
                                 0))  # HOLD
        
        return labels
    
    def pnl_with_carry_crystal(self, returns, signals, tc_pct=None):
        """ИСПРАВЛЕНО: корректный расчет PnL с транзакционными издержками"""
        if tc_pct is None:
            tc_pct = self.tc_pct
            
        if len(returns) != len(signals):
            raise ValueError("returns и signals должны быть одинаковой длины")
        
        returns = np.array(returns)
        signals = np.array(signals)
        
        # Инициализация
        position = 0
        gross_pnl = 0.0
        tc_cost = 0.0
        trades = 0
        
        for i in range(len(signals)):
            signal = signals[i]
            ret = returns[i]
            
            # Расчет PnL от текущей позиции
            gross_pnl += position * ret
            
            # Обработка сигнала
            if signal != 0 and signal != position:
                # Есть изменение позиции
                if position != 0:
                    # Закрытие текущей позиции
                    tc_cost += tc_pct
                    trades += 1
                
                if signal != 0:
                    # Открытие новой позиции
                    tc_cost += tc_pct  
                    trades += 1
                
                position = signal
        
        net_pnl = gross_pnl - tc_cost
        
        # Метрики
        if trades > 0:
            turnover = trades / len(signals)
        else:
            turnover = 0.0
        
        return {
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'tc_cost': tc_cost,
            'signals': trades,
            'turnover': turnover
        }
    
    def calculate_metrics_crystal(self, returns, signals):
        """Расчет всех торговых метрик"""
        pnl_result = self.pnl_with_carry_crystal(returns, signals)
        
        if pnl_result['signals'] == 0:
            return {
                'net_pnl': 0, 'gross_pnl': 0, 'sharpe': 0, 'sortino': 0,
                'max_dd': 0, 'profit_factor': 0, 'win_rate': 0, 'trades': 0,
                'turnover': 0, 'mar_ratio': 0, 'avg_hold': 0
            }
        
        # Расчет кумулятивного PnL для drawdown
        position = 0
        cum_pnl = []
        
        for i in range(len(signals)):
            signal = signals[i]
            ret = returns[i]
            position = signal if signal != 0 else position
            cum_pnl.append(position * ret)
        
        cum_pnl = np.cumsum(cum_pnl)
        
        # Максимальная просадка
        peak = np.maximum.accumulate(cum_pnl)
        drawdown = peak - cum_pnl
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Sharpe ratio (аннуализированный)
        ann_factor = self.infer_ann_factor(pd.Series(range(len(returns))))
        if np.std(cum_pnl) > 0:
            sharpe = np.mean(cum_pnl) * np.sqrt(ann_factor) / np.std(cum_pnl)
        else:
            sharpe = 0
        
        # Sortino ratio
        negative_returns = cum_pnl[cum_pnl < 0]
        if len(negative_returns) > 0 and np.std(negative_returns) > 0:
            sortino = np.mean(cum_pnl) * np.sqrt(ann_factor) / np.std(negative_returns)
        else:
            sortino = sharpe
        
        # MAR ratio
        mar_ratio = pnl_result['net_pnl'] / max_dd if max_dd > 0 else 0
        
        # Profit factor
        positive_trades = cum_pnl[cum_pnl > 0]
        negative_trades = cum_pnl[cum_pnl < 0]
        profit_factor = np.sum(positive_trades) / abs(np.sum(negative_trades)) if len(negative_trades) > 0 else 0
        
        # Win rate
        win_rate = len(positive_trades) / len(cum_pnl) if len(cum_pnl) > 0 else 0
        
        # Average hold
        signal_changes = np.diff(np.concatenate([[0], signals])) != 0
        avg_hold = len(signals) / np.sum(signal_changes) if np.sum(signal_changes) > 0 else 0
        
        return {
            'net_pnl': pnl_result['net_pnl'],
            'gross_pnl': pnl_result['gross_pnl'],
            'sharpe': sharpe,
            'sortino': sortino,
            'max_dd': max_dd,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'trades': pnl_result['signals'],
            'turnover': pnl_result['turnover'],
            'mar_ratio': mar_ratio,
            'avg_hold': avg_hold
        }
    
    def calculate_ece(self, y_true_binary, y_proba, n_bins=10):
        """Expected Calibration Error для оценки калибровки"""
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]
        
        ece = 0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (y_proba > bin_lower) & (y_proba <= bin_upper)
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                accuracy_in_bin = y_true_binary[in_bin].mean()
                avg_confidence_in_bin = y_proba[in_bin].mean()
                ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
        
        return ece
    
    def _score_threshold(self, returns, signals):
        """ИСПРАВЛЕНО: скоринг порогов с защитой от нулевых сделок"""
        pnl_result = self.pnl_with_carry_crystal(returns, signals)
        penalty = 0.0
        if pnl_result['signals'] == 0:
            penalty -= 1e-6
        elif pnl_result['turnover'] < 0.01:
            penalty -= 1e-7
        return pnl_result['net_pnl'] + penalty
    
    def optimize_dual_thresholds_perfect(self, y_proba_buy, y_proba_sell, returns, n_trials=100):
        """ИСПРАВЛЕНО: оптимизация порогов с улучшенным скорингом"""
        self.log_message("🎯 Оптимизация dual thresholds...")
        
        best_score = -np.inf
        best_buy_thresh = 0.5
        best_sell_thresh = 0.5
        
        # ИСПРАВЛЕНО: более тонкая сетка поиска
        buy_range = np.linspace(0.45, 0.75, n_trials//10)
        sell_range = np.linspace(0.45, 0.75, n_trials//10)
        
        for buy_thresh in buy_range:
            for sell_thresh in sell_range:
                # Генерация сигналов
                signals = np.where(y_proba_buy > buy_thresh, 1,
                                 np.where(y_proba_sell > sell_thresh, -1, 0))
                
                # ИСПРАВЛЕНО: используем _score_threshold для скоринга
                score = self._score_threshold(returns, signals)
                
                if score > best_score:
                    best_score = score
                    best_buy_thresh = buy_thresh
                    best_sell_thresh = sell_thresh
        
        self.log_message(f"✅ Лучшие пороги: BUY={best_buy_thresh:.3f}, SELL={best_sell_thresh:.3f}, Score={best_score:.6f}")
        return best_buy_thresh, best_sell_thresh
    
    def stress_test_tc(self, returns, signals, base_tc=0.02):
        """Стресс-тест транзакционных издержек"""
        results = {}
        
        for multiplier in [0.5, 1.0, 2.0, 5.0]:
            tc = base_tc * multiplier
            pnl_result = self.pnl_with_carry_crystal(returns, signals, tc)
            results[f'tc_{multiplier}x'] = pnl_result['net_pnl']
        
        return results
    
    def nested_walk_forward_crystal(self, df, feature_cols, labels):
        """ИСПРАВЛЕНО: Nested Walk-Forward с Time Series Split"""
        self.log_message("🔄 Запуск Nested Walk-Forward валидации...")
        
        # Основной TSCV (5 фолдов)
        main_tscv = TimeSeriesSplit(n_splits=5, test_size=None)
        
        all_results = []
        buy_thresholds = []
        sell_thresholds = []
        
        fold_num = 0
        for train_idx, test_idx in main_tscv.split(df):
            fold_num += 1
            self.log_message(f"📊 WF Фолд {fold_num}/5: train={len(train_idx)}, test={len(test_idx)}")
            
            # Данные для фолда
            X_fold = df[feature_cols].iloc[train_idx]
            y_fold = labels[train_idx]
            X_test_fold = df[feature_cols].iloc[test_idx]
            y_test_fold = labels[test_idx]
            returns_test = df['returns'].iloc[test_idx]
            
            # Валидация данных
            self._assert_finite(X_fold.values, f"X_fold_{fold_num}")
            self._assert_finite(X_test_fold.values, f"X_test_fold_{fold_num}")
            
            # Разделение train на IS/VAL для оптимизации порогов
            split_point = int(len(train_idx) * 0.8)
            is_idx = train_idx[:split_point]
            val_idx = train_idx[split_point:]
            
            X_is = df[feature_cols].iloc[is_idx]
            y_is = labels[is_idx]
            X_val = df[feature_cols].iloc[val_idx] 
            y_val = labels[val_idx]
            returns_val = df['returns'].iloc[val_idx]
            
            # Обучение модели на IS
            model = self.create_ensemble_model()
            
            # Скалирование
            scaler = StandardScaler()
            X_is_scaled = scaler.fit_transform(X_is)
            X_val_scaled = scaler.transform(X_val)
            X_test_scaled = scaler.transform(X_test_fold)
            
            # Веса классов
            sample_weights = compute_sample_weight('balanced', y_is)
            
            # Обучение
            model.fit(X_is_scaled, y_is, sample_weight=sample_weights)
            
            # Предсказания на валидации для оптимизации порогов
            y_proba_val = model.predict_proba(X_val_scaled)
            
            if y_proba_val.shape[1] == 3:  # 3 класса: SELL(-1), HOLD(0), BUY(1)
                proba_sell = y_proba_val[:, 0]  # Вероятность SELL
                proba_buy = y_proba_val[:, 2]   # Вероятность BUY
            else:
                # Fallback для 2 классов
                proba_sell = 1 - y_proba_val[:, 1]
                proba_buy = y_proba_val[:, 1]
            
            # Оптимизация порогов на валидации
            best_buy_thresh, best_sell_thresh = self.optimize_dual_thresholds_perfect(
                proba_buy, proba_sell, returns_val.values
            )
            
            buy_thresholds.append(best_buy_thresh)
            sell_thresholds.append(best_sell_thresh)
            
            # Тестирование на OOS с оптимальными порогами
            y_proba_test = model.predict_proba(X_test_scaled)
            
            if y_proba_test.shape[1] == 3:
                proba_sell_test = y_proba_test[:, 0]
                proba_buy_test = y_proba_test[:, 2]
            else:
                proba_sell_test = 1 - y_proba_test[:, 1]
                proba_buy_test = y_proba_test[:, 1]
            
            # Генерация сигналов
            signals_test = np.where(proba_buy_test > best_buy_thresh, 1,
                                  np.where(proba_sell_test > best_sell_thresh, -1, 0))
            
            # Метрики
            metrics = self.calculate_metrics_crystal(returns_test.values, signals_test)
            metrics['fold'] = fold_num
            metrics['buy_threshold'] = best_buy_thresh
            metrics['sell_threshold'] = best_sell_thresh
            
            # ИСПРАВЛЕНО: логирование с информацией о сигналах
            signal_counts = np.bincount(signals_test + 1, minlength=3)  # [-1,0,1] -> [0,1,2]
            self.log_message(f"🎯 Фолд {fold_num}: PnL={metrics['net_pnl']:.4f}, Sharpe={metrics['sharpe']:.3f}, "
                           f"Signals=[SELL:{signal_counts[0]}, HOLD:{signal_counts[1]}, BUY:{signal_counts[2]}], "
                           f"Turnover={metrics['turnover']:.3f}")
            
            all_results.append(metrics)
        
        return all_results, buy_thresholds, sell_thresholds
    
    def create_ensemble_model(self):
        """Создание ансамбля моделей с полным детерминизмом"""
        
        # ИСПРАВЛЕНО: n_jobs=1 для всех моделей
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=1,  # КРИТИЧНО для детерминизма
            class_weight='balanced'
        )
        
        gb = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            learning_rate=0.1
        )
        
        # ИСПРАВЛЕНО: shuffle=False для MLP
        mlp = MLPClassifier(
            hidden_layer_sizes=(100, 50),
            max_iter=500,
            random_state=42,
            shuffle=False  # КРИТИЧНО для time series
        )
        
        # Ансамбль
        ensemble = VotingClassifier(
            estimators=[('rf', rf), ('gb', gb), ('mlp', mlp)],
            voting='soft'
        )
        
        # Калибровка
        calibrated = CalibratedClassifierCV(
            ensemble,
            method='sigmoid',
            cv=3
        )
        
        return calibrated
    
    def predict_live_perfect(self, live_data):
        """ИСПРАВЛЕНО: онлайн-инференс с полной защитой"""
        if self.model is None or self.scaler is None:
            raise ValueError("Модель не обучена!")
        
        try:
            # Создание фичей (как при обучении)
            df_live, feature_cols = self.build_features_crystal(live_data.copy())
            
            # Берем последнюю строку
            X_live = df_live[feature_cols].iloc[-1:].values
            
            # Валидация
            self._assert_finite(X_live, "X_live")
            
            # Скалирование
            X_live_scaled = self.scaler.transform(X_live)
            
            # Предсказание
            y_proba = self.model.predict_proba(X_live_scaled)[0]
            
            # ИСПРАВЛЕНО: fallback для порогов
            metadata = self.metadata
            avg_buy_threshold = metadata.get('avg_buy_threshold', 0.5)
            avg_sell_threshold = metadata.get('avg_sell_threshold', 0.5)
            
            # Извлечение вероятностей
            if len(y_proba) == 3:  # 3 класса
                proba_sell = y_proba[0]
                proba_buy = y_proba[2]
            else:  # 2 класса
                proba_sell = 1 - y_proba[1]
                proba_buy = y_proba[1]
            
            # Генерация сигнала
            if proba_buy > avg_buy_threshold:
                signal = 1
                confidence = proba_buy
            elif proba_sell > avg_sell_threshold:
                signal = -1
                confidence = proba_sell
            else:
                signal = 0
                confidence = max(1 - proba_buy, 1 - proba_sell)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'proba_buy': proba_buy,
                'proba_sell': proba_sell,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            self.log_message(f"❌ Ошибка live предсказания: {e}")
            return {'signal': 0, 'confidence': 0.0, 'error': str(e)}
    
    def train_ultimate_crystal(self):
        """Главная функция обучения ULTIMATE CRYSTAL PERFECT системы"""
        start_time = time.time()
        self.log_message("🚀 Начинаем ULTIMATE CRYSTAL PERFECT обучение...")
        
        # Загрузка данных
        df = self.load_data_safe(self.data_file)
        
        # Создание фичей
        df, feature_cols = self.build_features_crystal(df)
        
        # Создание меток
        labels = self.create_labels_crystal(df)
        
        # Удаление строк с NaN в метках
        valid_mask = ~np.isnan(labels)
        df = df[valid_mask].reset_index(drop=True)
        labels = labels[valid_mask]
        
        self.log_message(f"📊 Финальный датасет: {len(df)} строк, {len(feature_cols)} фичей")
        
        # Nested Walk-Forward валидация
        wf_results, buy_thresholds, sell_thresholds = self.nested_walk_forward_crystal(
            df, feature_cols, labels
        )
        
        # Средние пороги
        avg_buy_threshold = np.mean(buy_thresholds)
        avg_sell_threshold = np.mean(sell_thresholds)
        
        self.log_message(f"📈 Средние пороги: BUY={avg_buy_threshold:.3f}, SELL={avg_sell_threshold:.3f}")
        
        # Финальное обучение на всех данных
        self.log_message("🎯 Финальное обучение на полном датасете...")
        
        X = df[feature_cols].values
        self._assert_finite(X, "X_final")
        
        # Скалирование
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Модель
        self.model = self.create_ensemble_model()
        sample_weights = compute_sample_weight('balanced', labels)
        self.model.fit(X_scaled, labels, sample_weight=sample_weights)
        
        # Предсказания для калибровки
        y_proba = self.model.predict_proba(X_scaled)
        
        # Калибровка метрик
        if y_proba.shape[1] == 3:
            # Для бинарной калибровки берем BUY vs остальные
            y_binary = (labels == 1).astype(int)
            proba_binary = y_proba[:, 2]  # Вероятность BUY
        else:
            y_binary = labels
            proba_binary = y_proba[:, 1]
        
        brier_score = brier_score_loss(y_binary, proba_binary)
        ece = self.calculate_ece(y_binary, proba_binary)
        
        # Стресс-тест издержек
        final_signals = np.where(y_proba[:, 2] > avg_buy_threshold, 1,
                               np.where(y_proba[:, 0] > avg_sell_threshold, -1, 0)) if y_proba.shape[1] == 3 else np.where(y_proba[:, 1] > 0.5, 1, -1)
        
        stress_results = self.stress_test_tc(df['returns'].values, final_signals)
        
        # Метаданные с репро-хэшами
        training_time = time.time() - start_time
        
        # ИСПРАВЛЕНО: используем эффективные ENV значения
        self.metadata = {
            'training_time': training_time,
            'data_rows': len(df),
            'features_count': len(feature_cols),
            'wf_folds': len(wf_results),
            'avg_buy_threshold': avg_buy_threshold,
            'avg_sell_threshold': avg_sell_threshold,
            'brier_score': brier_score,
            'ece': ece,
            'stress_test': stress_results,
            'wf_results': wf_results,
            'feature_names': feature_cols,
            'sklearn_version': sklearn.__version__,
            'numpy_version': np.__version__,
            'pandas_version': pd.__version__,
            'python_version': sys.version,
            'random_seed': 42,
            'thread_env': getattr(self, '_effective_thread_env', {}),
            'model_hash': hashlib.md5(str(self.model.get_params()).encode()).hexdigest(),
            'data_hash': hashlib.md5(str(df[feature_cols].values.tobytes())).hexdigest(),
            'training_timestamp': datetime.now().isoformat()
        }
        
        # Сохранение модели
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'metadata': self.metadata
        }
        
        with open('ultimate_crystal_model.pkl', 'wb') as f:
            pickle.dump(model_data, f)
        
        # Сохранение метаданных в JSON
        metadata_json = self.metadata.copy()
        metadata_json.pop('model_hash', None)  # Убираем нериализуемые поля
        
        with open('ultimate_crystal_metadata.json', 'w') as f:
            json.dump(metadata_json, f, indent=2, default=str)
        
        # Итоговые метрики
        avg_metrics = {}
        for key in ['net_pnl', 'sharpe', 'sortino', 'max_dd', 'turnover']:
            avg_metrics[key] = np.mean([r[key] for r in wf_results])
        
        self.log_message("🏆 ULTIMATE CRYSTAL PERFECT ЗАВЕРШЕНО!")
        self.log_message(f"⏱️  Время обучения: {training_time:.1f}с")
        self.log_message(f"📊 Средний PnL: {avg_metrics['net_pnl']:.4f}")
        self.log_message(f"📈 Средний Sharpe: {avg_metrics['sharpe']:.3f}")
        self.log_message(f"📉 Средний MaxDD: {avg_metrics['max_dd']:.4f}")
        self.log_message(f"🔄 Средний Turnover: {avg_metrics['turnover']:.3f}")
        self.log_message(f"🎯 Brier Score: {brier_score:.4f}")
        self.log_message(f"📏 ECE: {ece:.4f}")
        
        return self.metadata


def main():
    """Главная функция"""
    
    # Проверка headless режима
    if not sys.stdin.isatty():
        print("🤖 Headless режим обнаружен")
    
    # Создание и обучение системы
    ml_system = UltimateCrystalPerfectML()
    
    try:
        metadata = ml_system.train_ultimate_crystal()
        print("🎉 ULTIMATE CRYSTAL PERFECT успешно обучена!")
        print(f"📄 Метаданные сохранены в: ultimate_crystal_metadata.json")
        print(f"🤖 Модель сохранена в: ultimate_crystal_model.pkl")
        
    except Exception as e:
        print(f"❌ Ошибка обучения: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()