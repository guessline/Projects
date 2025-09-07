"""
Triple Barrier Labeling Implementation

Создает метки на основе трех барьеров:
1. Profit Target (верхний барьер) = +k * ATR
2. Stop Loss (нижний барьер) = -k * ATR  
3. Time Barrier (вертикальный барьер) = максимальное время удержания

Автор: Trading System Developer
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class TripleBarrierLabeler:
    """
    Класс для создания меток методом triple barrier
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация labeler'а
        
        Args:
            config: Конфигурация с параметрами triple barrier
        """
        self.config = config or self._default_config()
        self.logger = self._setup_logging()
        
        # Параметры из конфига
        self.profit_multiplier = self.config.get('profit_target_multiplier', 2.0)
        self.stop_multiplier = self.config.get('stop_loss_multiplier', 1.0)
        self.max_holding_bars = self.config.get('max_holding_bars', 48)
        self.atr_period = self.config.get('atr_period', 14)
        self.dynamic_barriers = self.config.get('dynamic_barriers', True)
        self.barrier_decay = self.config.get('barrier_decay', False)
        
        self.logger.info(f"TripleBarrierLabeler инициализирован с параметрами:")
        self.logger.info(f"  Profit multiplier: {self.profit_multiplier}")
        self.logger.info(f"  Stop multiplier: {self.stop_multiplier}")
        self.logger.info(f"  Max holding bars: {self.max_holding_bars}")
        self.logger.info(f"  ATR period: {self.atr_period}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            'profit_target_multiplier': 2.0,
            'stop_loss_multiplier': 1.0,
            'max_holding_bars': 48,
            'atr_period': 14,
            'dynamic_barriers': True,
            'barrier_decay': False
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logger = logging.getLogger('TripleBarrier')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def calculate_atr(self, data: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Расчет Average True Range
        
        Args:
            data: DataFrame с OHLC данными
            period: Период для расчета ATR
            
        Returns:
            Series с значениями ATR
        """
        if period is None:
            period = self.atr_period
            
        # Проверяем наличие необходимых колонок
        required_cols = ['high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Отсутствуют колонки: {missing_cols}")
        
        # Расчет True Range
        high_low = data['high'] - data['low']
        high_close_prev = np.abs(data['high'] - data['close'].shift(1))
        low_close_prev = np.abs(data['low'] - data['close'].shift(1))
        
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        
        # Расчет ATR как экспоненциальная скользящая средняя TR
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr
    
    def get_barriers(self, 
                    data: pd.DataFrame,
                    entry_prices: pd.Series,
                    side: pd.Series,
                    atr: pd.Series = None) -> Dict[str, pd.Series]:
        """
        Расчет барьеров для каждой позиции
        
        Args:
            data: DataFrame с ценовыми данными
            entry_prices: Цены входа
            side: Направление позиций (1 для long, -1 для short, 0 для hold)
            atr: Значения ATR (если None, рассчитывается автоматически)
            
        Returns:
            Dict с барьерами: profit_target, stop_loss, time_barrier
        """
        if atr is None:
            atr = self.calculate_atr(data)
        
        # Инициализация барьеров
        profit_targets = pd.Series(index=entry_prices.index, dtype=float)
        stop_losses = pd.Series(index=entry_prices.index, dtype=float)
        time_barriers = pd.Series(index=entry_prices.index, dtype='datetime64[ns]')
        
        for idx in entry_prices.index:
            if pd.isna(entry_prices[idx]) or side[idx] == 0:
                continue
                
            entry_price = entry_prices[idx]
            position_side = side[idx]
            current_atr = atr[idx]
            
            if pd.isna(current_atr):
                continue
            
            # Расчет барьеров в зависимости от направления
            if position_side == 1:  # Long position
                profit_targets[idx] = entry_price + (current_atr * self.profit_multiplier)
                stop_losses[idx] = entry_price - (current_atr * self.stop_multiplier)
            elif position_side == -1:  # Short position  
                profit_targets[idx] = entry_price - (current_atr * self.profit_multiplier)
                stop_losses[idx] = entry_price + (current_atr * self.stop_multiplier)
            
            # Временной барьер
            if isinstance(data.index, pd.DatetimeIndex):
                time_barriers[idx] = idx + pd.Timedelta(
                    minutes=self.max_holding_bars * 15  # Предполагаем M15 таймфрейм
                )
            else:
                # Если индекс не datetime, используем количество баров
                current_loc = data.index.get_loc(idx)
                max_loc = min(len(data) - 1, current_loc + self.max_holding_bars)
                time_barriers[idx] = data.index[max_loc]
        
        return {
            'profit_target': profit_targets,
            'stop_loss': stop_losses, 
            'time_barrier': time_barriers
        }
    
    def apply_barriers(self,
                      data: pd.DataFrame,
                      entry_prices: pd.Series,
                      side: pd.Series,
                      barriers: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Применение барьеров и определение результатов сделок
        
        Args:
            data: DataFrame с ценовыми данными
            entry_prices: Цены входа
            side: Направление позиций
            barriers: Барьеры (из get_barriers)
            
        Returns:
            DataFrame с результатами: exit_time, exit_price, return, label
        """
        results = []
        
        for entry_idx in entry_prices.index:
            if pd.isna(entry_prices[entry_idx]) or side[entry_idx] == 0:
                continue
            
            entry_price = entry_prices[entry_idx]
            position_side = side[entry_idx]
            
            # Получаем барьеры для данной позиции
            profit_target = barriers['profit_target'][entry_idx]
            stop_loss = barriers['stop_loss'][entry_idx]
            time_barrier = barriers['time_barrier'][entry_idx]
            
            if pd.isna(profit_target) or pd.isna(stop_loss):
                continue
            
            # Находим данные после входа
            entry_loc = data.index.get_loc(entry_idx)
            future_data = data.iloc[entry_loc + 1:]
            
            if len(future_data) == 0:
                continue
            
            # Поиск первого касания барьера
            exit_info = self._find_first_barrier_touch(
                future_data, entry_price, position_side,
                profit_target, stop_loss, time_barrier
            )
            
            if exit_info is not None:
                exit_time, exit_price, barrier_type = exit_info
                
                # Расчет доходности
                if position_side == 1:  # Long
                    return_pct = (exit_price - entry_price) / entry_price
                else:  # Short
                    return_pct = (entry_price - exit_price) / entry_price
                
                # Определение метки
                if barrier_type == 'profit':
                    label = 1 if position_side == 1 else -1
                elif barrier_type == 'stop':
                    label = -1 if position_side == 1 else 1
                else:  # time barrier
                    label = 1 if return_pct > 0 else (-1 if return_pct < 0 else 0)
                
                results.append({
                    'entry_time': entry_idx,
                    'entry_price': entry_price,
                    'exit_time': exit_time,
                    'exit_price': exit_price,
                    'side': position_side,
                    'return': return_pct,
                    'label': label,
                    'barrier_type': barrier_type,
                    'holding_period': self._calculate_holding_period(entry_idx, exit_time)
                })
        
        return pd.DataFrame(results)
    
    def _find_first_barrier_touch(self,
                                 future_data: pd.DataFrame,
                                 entry_price: float,
                                 side: int,
                                 profit_target: float,
                                 stop_loss: float,
                                 time_barrier) -> Optional[Tuple]:
        """
        Находит первое касание любого из барьеров
        
        Returns:
            Tuple (exit_time, exit_price, barrier_type) или None
        """
        for idx, row in future_data.iterrows():
            # Проверка временного барьера
            if isinstance(time_barrier, pd.Timestamp) and idx >= time_barrier:
                return (idx, row['close'], 'time')
            elif not isinstance(time_barrier, pd.Timestamp):
                # Если time_barrier - это индекс
                if idx >= time_barrier:
                    return (idx, row['close'], 'time')
            
            # Проверка ценовых барьеров
            if side == 1:  # Long position
                if row['high'] >= profit_target:
                    return (idx, profit_target, 'profit')
                elif row['low'] <= stop_loss:
                    return (idx, stop_loss, 'stop')
            else:  # Short position
                if row['low'] <= profit_target:
                    return (idx, profit_target, 'profit')
                elif row['high'] >= stop_loss:
                    return (idx, stop_loss, 'stop')
        
        # Если не достигли ни одного барьера, выходим по времени
        if len(future_data) > 0:
            last_idx = future_data.index[-1]
            last_price = future_data.iloc[-1]['close']
            return (last_idx, last_price, 'time')
        
        return None
    
    def _calculate_holding_period(self, entry_time, exit_time) -> int:
        """Расчет периода удержания позиции в барах"""
        if isinstance(entry_time, pd.Timestamp) and isinstance(exit_time, pd.Timestamp):
            return int((exit_time - entry_time).total_seconds() / (15 * 60))  # M15
        else:
            # Если индексы числовые
            return exit_time - entry_time
    
    def create_labels(self,
                     data: pd.DataFrame,
                     entry_signals: pd.Series,
                     side_signals: pd.Series = None) -> pd.DataFrame:
        """
        Главный метод для создания меток
        
        Args:
            data: DataFrame с OHLC данными (обязательно: open, high, low, close)
            entry_signals: Series с ценами входа (NaN для отсутствия сигнала)
            side_signals: Series с направлением (1=long, -1=short, 0=hold)
            
        Returns:
            DataFrame с метками и результатами сделок
        """
        self.logger.info("Начинаем создание triple barrier меток")
        self.logger.info(f"Данные: {len(data)} баров, {entry_signals.notna().sum()} сигналов")
        
        # Если side_signals не указан, определяем автоматически
        if side_signals is None:
            side_signals = pd.Series(1, index=entry_signals.index)  # Все long по умолчанию
            side_signals[entry_signals.isna()] = 0
        
        # Расчет ATR
        atr = self.calculate_atr(data)
        self.logger.info(f"ATR рассчитан, среднее значение: {atr.mean():.6f}")
        
        # Получение барьеров
        barriers = self.get_barriers(data, entry_signals, side_signals, atr)
        
        # Применение барьеров
        results = self.apply_barriers(data, entry_signals, side_signals, barriers)
        
        if len(results) > 0:
            self.logger.info(f"Создано {len(results)} меток")
            self.logger.info(f"Распределение меток: {results['label'].value_counts().to_dict()}")
            self.logger.info(f"Средняя доходность: {results['return'].mean():.4f}")
            self.logger.info(f"Среднее время удержания: {results['holding_period'].mean():.1f} баров")
        else:
            self.logger.warning("Не создано ни одной метки!")
        
        return results
    
    def get_statistics(self, results: pd.DataFrame) -> Dict[str, Any]:
        """
        Получение статистики по созданным меткам
        
        Args:
            results: DataFrame с результатами (из create_labels)
            
        Returns:
            Dict со статистикой
        """
        if len(results) == 0:
            return {}
        
        stats = {
            'total_trades': len(results),
            'label_distribution': results['label'].value_counts().to_dict(),
            'avg_return': results['return'].mean(),
            'std_return': results['return'].std(),
            'win_rate': (results['return'] > 0).mean(),
            'avg_holding_period': results['holding_period'].mean(),
            'max_holding_period': results['holding_period'].max(),
            'barrier_type_distribution': results['barrier_type'].value_counts().to_dict(),
            'profit_factor': self._calculate_profit_factor(results),
            'sharpe_ratio': self._calculate_sharpe_ratio(results)
        }
        
        return stats
    
    def _calculate_profit_factor(self, results: pd.DataFrame) -> float:
        """Расчет Profit Factor"""
        profits = results[results['return'] > 0]['return'].sum()
        losses = abs(results[results['return'] < 0]['return'].sum())
        
        if losses == 0:
            return float('inf') if profits > 0 else 0
        
        return profits / losses
    
    def _calculate_sharpe_ratio(self, results: pd.DataFrame, risk_free_rate: float = 0) -> float:
        """Расчет Sharpe Ratio"""
        returns = results['return']
        excess_returns = returns - risk_free_rate
        
        if excess_returns.std() == 0:
            return 0
        
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)  # Аннуализированный


def create_sample_data_with_signals():
    """Создание примера данных для тестирования"""
    np.random.seed(42)
    
    # Генерируем синтетические OHLC данные
    n_bars = 1000
    dates = pd.date_range(start='2023-01-01', periods=n_bars, freq='15min')
    
    # Случайное блуждание для цены закрытия
    price_changes = np.random.normal(0, 0.001, n_bars)
    close_prices = 100 * np.exp(np.cumsum(price_changes))
    
    # Генерируем OHLC на основе close
    high_noise = np.abs(np.random.normal(0, 0.002, n_bars))
    low_noise = np.abs(np.random.normal(0, 0.002, n_bars))
    open_noise = np.random.normal(0, 0.001, n_bars)
    
    data = pd.DataFrame({
        'datetime': dates,
        'open': close_prices + open_noise,
        'high': close_prices + high_noise,
        'low': close_prices - low_noise,
        'close': close_prices
    })
    
    data.set_index('datetime', inplace=True)
    
    # Создаем случайные сигналы входа
    entry_signals = pd.Series(index=data.index, dtype=float)
    side_signals = pd.Series(index=data.index, dtype=int)
    
    # Генерируем сигналы с вероятностью 5%
    signal_probability = 0.05
    for idx in data.index[50:]:  # Пропускаем первые 50 баров
        if np.random.random() < signal_probability:
            entry_signals[idx] = data.loc[idx, 'close']
            side_signals[idx] = np.random.choice([1, -1])  # Long или Short
        else:
            side_signals[idx] = 0
    
    return data, entry_signals, side_signals


if __name__ == "__main__":
    # Пример использования
    print("Тестирование Triple Barrier Labeler...")
    
    # Создаем тестовые данные
    data, entry_signals, side_signals = create_sample_data_with_signals()
    print(f"Создано {len(data)} баров данных")
    print(f"Сгенерировано {entry_signals.notna().sum()} сигналов")
    
    # Создаем labeler
    config = {
        'profit_target_multiplier': 2.0,
        'stop_loss_multiplier': 1.0,
        'max_holding_bars': 48,
        'atr_period': 14
    }
    
    labeler = TripleBarrierLabeler(config)
    
    # Создаем метки
    results = labeler.create_labels(data, entry_signals, side_signals)
    
    if len(results) > 0:
        print(f"\nСоздано {len(results)} меток")
        print("\nСтатистика:")
        stats = labeler.get_statistics(results)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print(f"\nПример результатов:")
        print(results.head())
    else:
        print("Метки не созданы!")