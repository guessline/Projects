"""
Expected Value Calculator Implementation

Expected Value (EV) - математическое ожидание результата торговой операции.
Это ключевая метрика для принятия решений в алгоритмической торговле.

Формула EV для торговой сделки:
EV = P(win) * AvgWin - P(loss) * AvgLoss - TotalCosts

Где:
- P(win) - калиброванная вероятность выигрышной сделки
- AvgWin - средний выигрыш в случае успеха
- P(loss) - вероятность проигрышной сделки (1 - P(win))
- AvgLoss - средний проигрыш в случае неудачи
- TotalCosts - суммарные издержки (комиссии + проскальзывание)

Торговое правило: входим в позицию только если EV > 0

Автор: Trading System Developer
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class PositionSide(Enum):
    """Направление позиции"""
    LONG = 1
    SHORT = -1
    HOLD = 0


@dataclass
class TradingCosts:
    """Структура для хранения торговых издержек"""
    commission_rate: float = 0.0004  # Комиссия в долях (0.04%)
    slippage_rate: float = 0.0002    # Проскальзывание в долях (0.02%)
    spread_rate: float = 0.0001      # Спред в долях (0.01%)
    
    def total_cost_rate(self) -> float:
        """Суммарная ставка издержек"""
        return self.commission_rate + self.slippage_rate + self.spread_rate


@dataclass
class TradeParameters:
    """Параметры торговой сделки"""
    entry_price: float
    take_profit: float
    stop_loss: float
    position_size: float
    side: PositionSide
    probability: float
    costs: TradingCosts
    
    def profit_amount(self) -> float:
        """Размер прибыли при достижении take profit"""
        if self.side == PositionSide.LONG:
            return (self.take_profit - self.entry_price) * self.position_size
        else:  # SHORT
            return (self.entry_price - self.take_profit) * self.position_size
    
    def loss_amount(self) -> float:
        """Размер убытка при достижении stop loss"""
        if self.side == PositionSide.LONG:
            return abs((self.stop_loss - self.entry_price) * self.position_size)
        else:  # SHORT
            return abs((self.entry_price - self.stop_loss) * self.position_size)
    
    def total_costs(self) -> float:
        """Суммарные издержки сделки"""
        return self.entry_price * self.position_size * self.costs.total_cost_rate()


class ExpectedValueCalculator:
    """
    Класс для расчета Expected Value торговых сделок
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация EV калькулятора
        
        Args:
            config: Конфигурация с параметрами расчета EV
        """
        self.config = config or self._default_config()
        self.logger = self._setup_logging()
        
        # Параметры из конфига
        self.min_ev_threshold = self.config.get('min_ev_threshold', 0.0)
        self.min_probability_long = self.config.get('min_probability_long', 0.52)
        self.min_probability_short = self.config.get('min_probability_short', 0.48)
        self.risk_free_rate = self.config.get('risk_free_rate', 0.0)
        
        # Кеш для исторических данных
        self.historical_trades = []
        self.performance_metrics = {}
        
        self.logger.info(f"ExpectedValueCalculator инициализирован")
        self.logger.info(f"  Min EV threshold: {self.min_ev_threshold}")
        self.logger.info(f"  Min prob long: {self.min_probability_long}")
        self.logger.info(f"  Min prob short: {self.min_probability_short}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            'min_ev_threshold': 0.0,
            'min_probability_long': 0.52,
            'min_probability_short': 0.48,
            'risk_free_rate': 0.0,
            'kelly_fraction': 0.25,
            'max_position_size': 0.1
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logger = logging.getLogger('EVCalculator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def calculate_ev(self, trade_params: TradeParameters) -> Dict[str, float]:
        """
        Расчет Expected Value для торговой сделки
        
        Args:
            trade_params: Параметры торговой сделки
            
        Returns:
            Dict с результатами расчета EV
        """
        # Вероятности
        p_win = trade_params.probability
        p_loss = 1.0 - p_win
        
        # Размеры прибыли и убытка
        profit = trade_params.profit_amount()
        loss = trade_params.loss_amount()
        costs = trade_params.total_costs()
        
        # Expected Value
        ev_gross = p_win * profit - p_loss * loss
        ev_net = ev_gross - costs
        
        # Дополнительные метрики
        profit_factor = (p_win * profit) / (p_loss * loss) if p_loss * loss > 0 else float('inf')
        win_rate = p_win
        avg_win = profit
        avg_loss = loss
        
        # Risk-Reward Ratio
        risk_reward_ratio = profit / loss if loss > 0 else float('inf')
        
        # Kelly Criterion для оптимального размера позиции
        kelly_fraction = self._calculate_kelly_fraction(p_win, profit, loss)
        
        return {
            'ev_gross': ev_gross,
            'ev_net': ev_net,
            'profit_factor': profit_factor,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_costs': costs,
            'risk_reward_ratio': risk_reward_ratio,
            'kelly_fraction': kelly_fraction,
            'probability': p_win
        }
    
    def _calculate_kelly_fraction(self, 
                                p_win: float, 
                                avg_win: float, 
                                avg_loss: float) -> float:
        """
        Расчет оптимального размера позиции по Kelly Criterion
        
        Kelly% = (bp - q) / b
        где:
        b = отношение выигрыша к проигрышу
        p = вероятность выигрыша
        q = вероятность проигрыша (1-p)
        """
        if avg_loss <= 0:
            return 0.0
        
        b = avg_win / avg_loss  # Отношение win/loss
        p = p_win
        q = 1 - p_win
        
        kelly = (b * p - q) / b
        
        # Ограничиваем Kelly fraction разумными пределами
        kelly = max(0.0, min(kelly, self.config.get('kelly_fraction', 0.25)))
        
        return kelly
    
    def should_trade(self, 
                    trade_params: TradeParameters,
                    additional_filters: Dict[str, bool] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Принятие решения о входе в сделку на основе EV
        
        Args:
            trade_params: Параметры торговой сделки
            additional_filters: Дополнительные фильтры
            
        Returns:
            Tuple (решение_торговать, детали_расчета)
        """
        # Расчет EV
        ev_metrics = self.calculate_ev(trade_params)
        
        # Основные условия для входа
        conditions = {
            'ev_positive': ev_metrics['ev_net'] > self.min_ev_threshold,
            'probability_threshold': self._check_probability_threshold(trade_params),
            'risk_reward_acceptable': ev_metrics['risk_reward_ratio'] >= 1.0,
            'kelly_positive': ev_metrics['kelly_fraction'] > 0
        }
        
        # Применяем дополнительные фильтры
        if additional_filters:
            conditions.update(additional_filters)
        
        # Итоговое решение
        trade_decision = all(conditions.values())
        
        # Детали для логирования
        decision_details = {
            'trade_decision': trade_decision,
            'conditions': conditions,
            'ev_metrics': ev_metrics,
            'trade_params': {
                'side': trade_params.side.name,
                'probability': trade_params.probability,
                'entry_price': trade_params.entry_price,
                'take_profit': trade_params.take_profit,
                'stop_loss': trade_params.stop_loss
            }
        }
        
        return trade_decision, decision_details
    
    def _check_probability_threshold(self, trade_params: TradeParameters) -> bool:
        """Проверка порога вероятности в зависимости от направления"""
        if trade_params.side == PositionSide.LONG:
            return trade_params.probability >= self.min_probability_long
        elif trade_params.side == PositionSide.SHORT:
            return trade_params.probability <= (1 - self.min_probability_short)
        else:
            return False
    
    def batch_calculate_ev(self, 
                          trades_data: pd.DataFrame,
                          probability_column: str = 'probability',
                          side_column: str = 'side') -> pd.DataFrame:
        """
        Пакетный расчет EV для множества потенциальных сделок
        
        Args:
            trades_data: DataFrame с данными о сделках
            probability_column: Название колонки с вероятностями
            side_column: Название колонки с направлением
            
        Returns:
            DataFrame с результатами расчета EV
        """
        results = []
        
        for idx, row in trades_data.iterrows():
            try:
                # Создаем параметры сделки
                costs = TradingCosts(
                    commission_rate=row.get('commission_rate', 0.0004),
                    slippage_rate=row.get('slippage_rate', 0.0002),
                    spread_rate=row.get('spread_rate', 0.0001)
                )
                
                side = PositionSide.LONG if row[side_column] == 1 else PositionSide.SHORT
                
                trade_params = TradeParameters(
                    entry_price=row['entry_price'],
                    take_profit=row['take_profit'],
                    stop_loss=row['stop_loss'],
                    position_size=row.get('position_size', 1.0),
                    side=side,
                    probability=row[probability_column],
                    costs=costs
                )
                
                # Расчет EV
                ev_metrics = self.calculate_ev(trade_params)
                ev_metrics['index'] = idx
                
                # Решение о торговле
                trade_decision, _ = self.should_trade(trade_params)
                ev_metrics['trade_decision'] = trade_decision
                
                results.append(ev_metrics)
                
            except Exception as e:
                self.logger.warning(f"Ошибка расчета EV для строки {idx}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def optimize_position_size(self,
                             trade_params: TradeParameters,
                             max_risk_per_trade: float = 0.02) -> float:
        """
        Оптимизация размера позиции на основе Kelly Criterion и риск-менеджмента
        
        Args:
            trade_params: Параметры торговой сделки
            max_risk_per_trade: Максимальный риск на сделку (доля от капитала)
            
        Returns:
            Оптимальный размер позиции
        """
        ev_metrics = self.calculate_ev(trade_params)
        
        # Kelly fraction
        kelly_size = ev_metrics['kelly_fraction']
        
        # Размер на основе максимального риска
        risk_per_unit = trade_params.loss_amount() / trade_params.position_size
        risk_based_size = max_risk_per_trade / risk_per_unit if risk_per_unit > 0 else 0
        
        # Выбираем минимальный размер для консервативности
        optimal_size = min(kelly_size, risk_based_size, self.config.get('max_position_size', 0.1))
        
        return max(0, optimal_size)
    
    def calculate_portfolio_ev(self, 
                             portfolio_trades: List[TradeParameters]) -> Dict[str, float]:
        """
        Расчет Expected Value для портфеля сделок
        
        Args:
            portfolio_trades: Список параметров сделок в портфеле
            
        Returns:
            Dict с метриками портфеля
        """
        if not portfolio_trades:
            return {}
        
        total_ev = 0
        total_risk = 0
        individual_evs = []
        
        for trade in portfolio_trades:
            ev_metrics = self.calculate_ev(trade)
            individual_evs.append(ev_metrics['ev_net'])
            total_ev += ev_metrics['ev_net']
            total_risk += trade.loss_amount()
        
        # Портфельные метрики
        portfolio_metrics = {
            'total_ev': total_ev,
            'avg_ev_per_trade': total_ev / len(portfolio_trades),
            'total_risk': total_risk,
            'ev_risk_ratio': total_ev / total_risk if total_risk > 0 else 0,
            'portfolio_sharpe': np.mean(individual_evs) / np.std(individual_evs) if np.std(individual_evs) > 0 else 0,
            'num_trades': len(portfolio_trades)
        }
        
        return portfolio_metrics
    
    def stress_test_ev(self,
                      trade_params: TradeParameters,
                      probability_scenarios: List[float],
                      cost_multipliers: List[float] = None) -> pd.DataFrame:
        """
        Стресс-тестирование EV при различных сценариях
        
        Args:
            trade_params: Базовые параметры сделки
            probability_scenarios: Список вероятностей для тестирования
            cost_multipliers: Множители для увеличения издержек
            
        Returns:
            DataFrame с результатами стресс-тестов
        """
        if cost_multipliers is None:
            cost_multipliers = [1.0, 1.5, 2.0, 3.0]
        
        results = []
        
        for prob in probability_scenarios:
            for cost_mult in cost_multipliers:
                # Модифицируем параметры
                modified_params = TradeParameters(
                    entry_price=trade_params.entry_price,
                    take_profit=trade_params.take_profit,
                    stop_loss=trade_params.stop_loss,
                    position_size=trade_params.position_size,
                    side=trade_params.side,
                    probability=prob,
                    costs=TradingCosts(
                        commission_rate=trade_params.costs.commission_rate * cost_mult,
                        slippage_rate=trade_params.costs.slippage_rate * cost_mult,
                        spread_rate=trade_params.costs.spread_rate * cost_mult
                    )
                )
                
                # Расчет EV
                ev_metrics = self.calculate_ev(modified_params)
                
                results.append({
                    'probability': prob,
                    'cost_multiplier': cost_mult,
                    'ev_net': ev_metrics['ev_net'],
                    'ev_gross': ev_metrics['ev_gross'],
                    'profit_factor': ev_metrics['profit_factor'],
                    'trade_viable': ev_metrics['ev_net'] > self.min_ev_threshold
                })
        
        return pd.DataFrame(results)
    
    def get_ev_statistics(self) -> Dict[str, Any]:
        """Получение статистики по рассчитанным EV"""
        if not self.historical_trades:
            return {}
        
        evs = [trade['ev_net'] for trade in self.historical_trades]
        
        return {
            'total_trades_analyzed': len(self.historical_trades),
            'avg_ev': np.mean(evs),
            'median_ev': np.median(evs),
            'std_ev': np.std(evs),
            'min_ev': np.min(evs),
            'max_ev': np.max(evs),
            'positive_ev_rate': np.mean([ev > 0 for ev in evs])
        }


def create_sample_ev_data():
    """Создание примера данных для тестирования EV калькулятора"""
    np.random.seed(42)
    
    n_trades = 100
    
    # Генерируем синтетические данные о потенциальных сделках
    data = []
    
    for i in range(n_trades):
        entry_price = 100 + np.random.normal(0, 10)
        atr = np.abs(np.random.normal(2, 0.5))
        
        # Take profit и stop loss на основе ATR
        tp_multiplier = np.random.uniform(1.5, 3.0)
        sl_multiplier = np.random.uniform(0.8, 1.5)
        
        side = np.random.choice([1, -1])
        
        if side == 1:  # Long
            take_profit = entry_price + atr * tp_multiplier
            stop_loss = entry_price - atr * sl_multiplier
        else:  # Short
            take_profit = entry_price - atr * tp_multiplier
            stop_loss = entry_price + atr * sl_multiplier
        
        # Вероятность с небольшим bias в сторону прибыльности
        probability = np.random.beta(2, 2) * 0.4 + 0.3  # Диапазон 0.3-0.7
        
        data.append({
            'entry_price': entry_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'position_size': 1.0,
            'side': side,
            'probability': probability,
            'commission_rate': 0.0004,
            'slippage_rate': 0.0002,
            'spread_rate': 0.0001
        })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Пример использования
    print("Тестирование Expected Value Calculator...")
    
    # Создаем EV калькулятор
    config = {
        'min_ev_threshold': 0.0,
        'min_probability_long': 0.52,
        'min_probability_short': 0.48
    }
    
    ev_calculator = ExpectedValueCalculator(config)
    
    # Создаем тестовые данные
    trades_data = create_sample_ev_data()
    print(f"Создано {len(trades_data)} потенциальных сделок")
    
    # Пакетный расчет EV
    ev_results = ev_calculator.batch_calculate_ev(trades_data)
    
    print(f"\nРезультаты расчета EV:")
    print(f"  Средний EV: {ev_results['ev_net'].mean():.4f}")
    print(f"  Медианный EV: {ev_results['ev_net'].median():.4f}")
    print(f"  Положительных EV: {(ev_results['ev_net'] > 0).sum()}/{len(ev_results)}")
    print(f"  Рекомендуемых сделок: {ev_results['trade_decision'].sum()}/{len(ev_results)}")
    
    # Пример индивидуальной сделки
    sample_trade = trades_data.iloc[0]
    
    costs = TradingCosts(
        commission_rate=sample_trade['commission_rate'],
        slippage_rate=sample_trade['slippage_rate'],
        spread_rate=sample_trade['spread_rate']
    )
    
    trade_params = TradeParameters(
        entry_price=sample_trade['entry_price'],
        take_profit=sample_trade['take_profit'],
        stop_loss=sample_trade['stop_loss'],
        position_size=sample_trade['position_size'],
        side=PositionSide.LONG if sample_trade['side'] == 1 else PositionSide.SHORT,
        probability=sample_trade['probability'],
        costs=costs
    )
    
    # Принятие решения
    trade_decision, details = ev_calculator.should_trade(trade_params)
    
    print(f"\nПример анализа сделки:")
    print(f"  Направление: {trade_params.side.name}")
    print(f"  Вероятность: {trade_params.probability:.3f}")
    print(f"  EV (нетто): {details['ev_metrics']['ev_net']:.4f}")
    print(f"  Profit Factor: {details['ev_metrics']['profit_factor']:.2f}")
    print(f"  Kelly Fraction: {details['ev_metrics']['kelly_fraction']:.3f}")
    print(f"  Решение: {'ТОРГОВАТЬ' if trade_decision else 'ПРОПУСТИТЬ'}")
    
    # Стресс-тест
    stress_scenarios = [0.4, 0.5, 0.6, 0.7]
    stress_results = ev_calculator.stress_test_ev(trade_params, stress_scenarios)
    
    print(f"\nСтресс-тест (жизнеспособных сценариев):")
    viable_scenarios = stress_results[stress_results['trade_viable']]
    print(f"  {len(viable_scenarios)}/{len(stress_results)} сценариев жизнеспособны")
    
    if len(viable_scenarios) > 0:
        print(f"  Лучший EV: {viable_scenarios['ev_net'].max():.4f}")
        print(f"  Худший EV: {viable_scenarios['ev_net'].min():.4f}")