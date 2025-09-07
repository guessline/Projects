# Ultimate Crystal Perfect Tank

Прибыльный портфельный интра-дей/свинговый алгоритм для MT5 с генерацией сигналов в Python.

## Архитектура проекта

```
ultimate_crystal_tank/
├── core/                   # Основные компоненты системы
│   ├── __init__.py
│   ├── triple_barrier.py   # Triple-barrier labeling
│   ├── meta_labeling.py    # Meta-labeling фильтр
│   ├── calibration.py      # Калибровка вероятностей
│   ├── ev_calculator.py    # Expected Value калькулятор
│   └── regime_filters.py   # Фильтры режимов рынка
├── data/                   # Модули работы с данными
│   ├── __init__.py
│   ├── loader.py          # Загрузка данных M15/H1
│   ├── features.py        # Генерация признаков
│   └── preprocessor.py    # Предобработка данных
├── models/                 # ML модели
│   ├── __init__.py
│   ├── base_model.py      # Базовая модель направления
│   ├── meta_model.py      # Meta-labeling модель
│   └── ensemble.py        # Ансамбль моделей
├── executors/              # Исполнители торговых решений
│   ├── __init__.py
│   ├── online_executor.py # Онлайн исполнитель для MT5
│   └── backtester.py      # Бэктестер
├── config/                 # Конфигурационные файлы
│   ├── portfolio.json     # Настройки портфеля
│   ├── trading.json       # Торговые параметры
│   └── instruments.json   # Параметры инструментов
├── reports/                # Отчетность
│   ├── __init__.py
│   ├── performance.py     # Анализ производительности
│   └── reporter.py        # Генерация отчетов
├── tests/                  # Тесты
│   └── __init__.py
├── utils/                  # Утилиты
│   ├── __init__.py
│   ├── risk_manager.py    # Риск-менеджмент
│   ├── portfolio_manager.py # Портфельный менеджер
│   └── validators.py      # Валидаторы
└── main.py                # Главный файл запуска
```

## Концепт

Mid-frequency, multi-asset, regime-aware EV-трейдинг с:

- **Triple-barrier labeling** (±k·ATR, вертикальный барьер)
- **Meta-labeling** для фильтрации входов
- **Калибровка вероятностей** (Platt/Isotonic)
- **EV-правило входа**: торгуем только если EV_side > 0
- **Фильтр режимов**: ATR-перцентиль>50 или ADX>18
- **Портфель**: крипто + FX/металлы для диверсификации

## Целевые метрики

### Бизнес-цели (портфель, нетто издержек)
- Доходность: 10-15% в месяц
- Sharpe (мес.): ≥0.8 портфельно
- Max DD (мес.): ≤12%

### OOS-критерии на инструмент
- ≥150-200 сделок; hit-rate ≥54-57%; PF ≥1.15
- Средняя сделка > 1.3× совокупных издержек
- Sharpe OOS ≥0.6 на инструмент

## Установка и запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Обучение моделей
python -m ultimate_crystal_tank.train_wf_meta

# Запуск онлайн-исполнителя
python -m ultimate_crystal_tank.online_executor_ev

# Генерация отчетов
python -m ultimate_crystal_tank.reports.reporter
```

## Этапы разработки

1. ✅ Data & labels (M15/H1) → triple-barrier
2. 🔄 WF base+meta + калибровка → отчёты OOS
3. ⏳ Отбор тикеров по критериям → формирование портфеля
4. ⏳ EV-исполнитель + риск → dry-run
5. ⏳ GO/NO-GO: проверка KPIs → продакшен MT5

## Риски и хеджирование

- **Edge-drift** → непрерывный WF-перетрен, авто-паузы
- **Издержки/проскальзывание** → стресс-тесты (+50…+200%)
- **Переобучение** → meta-label + калибровка + строгие OOS-критерии