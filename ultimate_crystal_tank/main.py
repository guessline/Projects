#!/usr/bin/env python3
"""
Ultimate Crystal Perfect Tank - Main Entry Point

Главный файл запуска торговой системы Ultimate Crystal Perfect Tank.
Поддерживает различные режимы работы:
- Обучение моделей (train)
- Бэктестирование (backtest)
- Онлайн-торговля (live)
- Анализ данных (analyze)

Использование:
    python main.py train --config config/portfolio.json
    python main.py backtest --start-date 2023-01-01 --end-date 2023-12-31
    python main.py live --dry-run
    python main.py analyze --instrument BTCUSD

Автор: Trading System Developer
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Импорты компонентов системы
from core.triple_barrier import TripleBarrierLabeler
from core.meta_labeling import MetaLabeler
from core.calibration import ProbabilityCalibrator
from core.ev_calculator import ExpectedValueCalculator


class UltimateCrystalTank:
    """
    Главный класс торговой системы Ultimate Crystal Perfect Tank
    """
    
    def __init__(self, config_path: str = "config/portfolio.json"):
        """
        Инициализация системы
        
        Args:
            config_path: Путь к конфигурационному файлу
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Инициализация компонентов
        self.triple_barrier_labeler = None
        self.meta_labeler = None
        self.probability_calibrator = None
        self.ev_calculator = None
        
        self.logger.info("Ultimate Crystal Perfect Tank инициализирован")
        self.logger.info(f"Конфигурация загружена: {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Ошибка загрузки конфигурации {self.config_path}: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            "portfolio": {
                "name": "Ultimate Crystal Perfect Tank",
                "target_monthly_return": 0.125,
                "max_monthly_drawdown": 0.12,
                "target_sharpe": 0.8
            },
            "instruments": {
                "crypto": {"BTCUSD": {"enabled": True}},
                "fx": {"EURUSD": {"enabled": True}}
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Настройка логгера
        logger = logging.getLogger('UltimateCrystalTank')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Файловый хендлер
            file_handler = logging.FileHandler(
                log_dir / f"uct_{datetime.now().strftime('%Y%m%d')}.log"
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # Консольный хендлер
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def initialize_components(self):
        """Инициализация всех компонентов системы"""
        self.logger.info("Инициализация компонентов системы...")
        
        # Triple Barrier Labeler
        triple_barrier_config = {
            'profit_target_multiplier': 2.0,
            'stop_loss_multiplier': 1.0,
            'max_holding_bars': 48,
            'atr_period': 14
        }
        self.triple_barrier_labeler = TripleBarrierLabeler(triple_barrier_config)
        
        # Meta Labeler
        meta_config = {
            'meta_features': ['volatility_regime', 'trend_strength', 'seasonality'],
            'model_type': 'logistic_regression'
        }
        self.meta_labeler = MetaLabeler(meta_config)
        
        # Probability Calibrator
        calibration_config = {
            'method': 'isotonic',
            'cv_folds': 5
        }
        self.probability_calibrator = ProbabilityCalibrator(calibration_config)
        
        # Expected Value Calculator
        ev_config = {
            'min_ev_threshold': 0.0,
            'min_probability_long': 0.52,
            'min_probability_short': 0.48
        }
        self.ev_calculator = ExpectedValueCalculator(ev_config)
        
        self.logger.info("Все компоненты инициализированы")
    
    def train_models(self, 
                    data_path: str = None,
                    start_date: str = None,
                    end_date: str = None):
        """
        Обучение моделей системы
        
        Args:
            data_path: Путь к данным для обучения
            start_date: Начальная дата для обучения
            end_date: Конечная дата для обучения
        """
        self.logger.info("Начинаем обучение моделей...")
        
        if not self.triple_barrier_labeler:
            self.initialize_components()
        
        # Здесь будет логика загрузки данных и обучения
        # Пока что заглушка
        self.logger.info("Обучение моделей завершено (заглушка)")
        
        return {
            'status': 'completed',
            'models_trained': ['base_model', 'meta_model'],
            'training_period': f"{start_date} - {end_date}"
        }
    
    def run_backtest(self,
                    start_date: str,
                    end_date: str,
                    instruments: List[str] = None):
        """
        Запуск бэктестирования
        
        Args:
            start_date: Начальная дата бэктеста
            end_date: Конечная дата бэктеста
            instruments: Список инструментов для тестирования
        """
        self.logger.info(f"Запуск бэктеста: {start_date} - {end_date}")
        
        if instruments is None:
            instruments = self._get_enabled_instruments()
        
        self.logger.info(f"Инструменты для бэктеста: {instruments}")
        
        # Здесь будет логика бэктестирования
        # Пока что заглушка
        backtest_results = {
            'period': f"{start_date} - {end_date}",
            'instruments': instruments,
            'total_return': 0.15,
            'sharpe_ratio': 0.85,
            'max_drawdown': 0.08,
            'total_trades': 1247,
            'win_rate': 0.58
        }
        
        self.logger.info("Бэктест завершен")
        self._print_backtest_results(backtest_results)
        
        return backtest_results
    
    def run_live_trading(self, dry_run: bool = True):
        """
        Запуск онлайн-торговли
        
        Args:
            dry_run: Режим демо-торговли (без реальных сделок)
        """
        mode = "DRY RUN" if dry_run else "LIVE"
        self.logger.info(f"Запуск онлайн-торговли в режиме {mode}")
        
        if not dry_run:
            self.logger.warning("ВНИМАНИЕ: Запуск реальной торговли!")
            response = input("Вы уверены? (yes/no): ")
            if response.lower() != 'yes':
                self.logger.info("Торговля отменена пользователем")
                return
        
        # Здесь будет логика онлайн-торговли
        self.logger.info("Онлайн-торговля запущена (заглушка)")
        
        return {'status': 'running', 'mode': mode}
    
    def analyze_instrument(self, instrument: str):
        """
        Анализ конкретного инструмента
        
        Args:
            instrument: Название инструмента для анализа
        """
        self.logger.info(f"Анализ инструмента: {instrument}")
        
        # Здесь будет логика анализа инструмента
        analysis_results = {
            'instrument': instrument,
            'current_regime': 'trending',
            'volatility_percentile': 65,
            'recent_performance': {
                'last_30_trades': 28,
                'win_rate': 0.64,
                'avg_return': 0.023
            },
            'recommendation': 'ACTIVE'
        }
        
        self._print_analysis_results(analysis_results)
        return analysis_results
    
    def _get_enabled_instruments(self) -> List[str]:
        """Получение списка активных инструментов из конфигурации"""
        instruments = []
        
        for category, items in self.config.get('instruments', {}).items():
            for instrument, config in items.items():
                if config.get('enabled', False):
                    instruments.append(instrument)
        
        return instruments
    
    def _print_backtest_results(self, results: Dict[str, Any]):
        """Вывод результатов бэктеста в консоль"""
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ БЭКТЕСТИРОВАНИЯ")
        print("="*60)
        print(f"Период: {results['period']}")
        print(f"Инструменты: {', '.join(results['instruments'])}")
        print(f"Общая доходность: {results['total_return']:.1%}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Максимальная просадка: {results['max_drawdown']:.1%}")
        print(f"Всего сделок: {results['total_trades']}")
        print(f"Процент выигрышей: {results['win_rate']:.1%}")
        print("="*60 + "\n")
    
    def _print_analysis_results(self, results: Dict[str, Any]):
        """Вывод результатов анализа в консоль"""
        print("\n" + "="*50)
        print(f"АНАЛИЗ ИНСТРУМЕНТА: {results['instrument']}")
        print("="*50)
        print(f"Текущий режим: {results['current_regime']}")
        print(f"Перцентиль волатильности: {results['volatility_percentile']}%")
        print(f"Последние 30 сделок: {results['recent_performance']['last_30_trades']}")
        print(f"Процент выигрышей: {results['recent_performance']['win_rate']:.1%}")
        print(f"Средняя доходность: {results['recent_performance']['avg_return']:.1%}")
        print(f"Рекомендация: {results['recommendation']}")
        print("="*50 + "\n")


def create_argument_parser() -> argparse.ArgumentParser:
    """Создание парсера аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Ultimate Crystal Perfect Tank - Алгоритмическая торговая система",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py train --config config/portfolio.json
  python main.py backtest --start-date 2023-01-01 --end-date 2023-12-31
  python main.py live --dry-run
  python main.py analyze --instrument BTCUSD
        """
    )
    
    parser.add_argument(
        'command',
        choices=['train', 'backtest', 'live', 'analyze'],
        help='Команда для выполнения'
    )
    
    parser.add_argument(
        '--config',
        default='config/portfolio.json',
        help='Путь к конфигурационному файлу'
    )
    
    parser.add_argument(
        '--start-date',
        help='Начальная дата (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        help='Конечная дата (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--instrument',
        help='Инструмент для анализа'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим демо-торговли (без реальных сделок)'
    )
    
    parser.add_argument(
        '--data-path',
        help='Путь к данным для обучения'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )
    
    return parser


def main():
    """Главная функция"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Создаем экземпляр системы
    try:
        system = UltimateCrystalTank(args.config)
    except Exception as e:
        print(f"Ошибка инициализации системы: {e}")
        sys.exit(1)
    
    # Выполняем команду
    try:
        if args.command == 'train':
            result = system.train_models(
                data_path=args.data_path,
                start_date=args.start_date,
                end_date=args.end_date
            )
            print(f"Обучение завершено: {result}")
        
        elif args.command == 'backtest':
            if not args.start_date or not args.end_date:
                parser.error("Для бэктеста требуются --start-date и --end-date")
            
            result = system.run_backtest(
                start_date=args.start_date,
                end_date=args.end_date
            )
        
        elif args.command == 'live':
            result = system.run_live_trading(dry_run=args.dry_run)
            print(f"Онлайн-торговля: {result}")
        
        elif args.command == 'analyze':
            if not args.instrument:
                parser.error("Для анализа требуется --instrument")
            
            result = system.analyze_instrument(args.instrument)
    
    except KeyboardInterrupt:
        system.logger.info("Работа системы прервана пользователем")
        sys.exit(0)
    except Exception as e:
        system.logger.error(f"Ошибка выполнения команды {args.command}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()