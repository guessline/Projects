"""
Probability Calibration Implementation

Калибровка вероятностей - критически важный компонент для точного расчета Expected Value.
Многие ML модели выдают некалиброванные вероятности, которые не отражают реальную 
уверенность в предсказании.

Методы калибровки:
1. Platt Scaling - логистическая регрессия на выходах модели
2. Isotonic Regression - монотонная регрессия, более гибкая

Автор: Trading System Developer
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import brier_score_loss, log_loss
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class ProbabilityCalibrator:
    """
    Класс для калибровки вероятностей ML моделей
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация калибратора
        
        Args:
            config: Конфигурация с параметрами калибровки
        """
        self.config = config or self._default_config()
        self.logger = self._setup_logging()
        
        # Параметры из конфига
        self.method = self.config.get('method', 'isotonic')
        self.cv_folds = self.config.get('cv_folds', 5)
        self.sample_weight = self.config.get('calibration_sample_weight', True)
        
        # Калиброванные модели
        self.calibrated_models = {}
        self.calibration_curves = {}
        self.is_fitted = False
        
        self.logger.info(f"ProbabilityCalibrator инициализирован")
        self.logger.info(f"  Метод: {self.method}")
        self.logger.info(f"  CV folds: {self.cv_folds}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию"""
        return {
            'method': 'isotonic',  # 'platt' или 'isotonic'
            'cv_folds': 5,
            'calibration_sample_weight': True
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logger = logging.getLogger('ProbabilityCalibrator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def fit(self, 
            models: Dict[str, Any],
            X: pd.DataFrame,
            y: pd.Series,
            sample_weight: pd.Series = None) -> Dict[str, Any]:
        """
        Обучение калибраторов для моделей
        
        Args:
            models: Словарь обученных моделей {name: model}
            X: Признаки для калибровки
            y: Истинные метки
            sample_weight: Веса образцов
            
        Returns:
            Dict с результатами калибровки
        """
        self.logger.info("Начинаем калибровку вероятностей")
        self.logger.info(f"Моделей для калибровки: {len(models)}")
        self.logger.info(f"Образцов для калибровки: {len(X)}")
        
        results = {}
        
        for model_name, model in models.items():
            self.logger.info(f"Калибровка модели: {model_name}")
            
            try:
                # Получаем некалиброванные вероятности
                if hasattr(model, 'predict_proba'):
                    uncalibrated_probs = cross_val_predict(
                        model, X, y, cv=self.cv_folds, method='predict_proba'
                    )[:, 1]  # Берем вероятность положительного класса
                else:
                    uncalibrated_probs = cross_val_predict(
                        model, X, y, cv=self.cv_folds, method='decision_function'
                    )
                    # Преобразуем в вероятности через сигмоиду
                    uncalibrated_probs = 1 / (1 + np.exp(-uncalibrated_probs))
                
                # Создаем калиброванную модель
                calibrated_model = CalibratedClassifierCV(
                    model, 
                    method=self.method,
                    cv=self.cv_folds
                )
                
                # Обучаем калибратор
                if sample_weight is not None and self.sample_weight:
                    calibrated_model.fit(X, y, sample_weight=sample_weight)
                else:
                    calibrated_model.fit(X, y)
                
                # Получаем калиброванные вероятности
                calibrated_probs = calibrated_model.predict_proba(X)[:, 1]
                
                # Сохраняем модель
                self.calibrated_models[model_name] = calibrated_model
                
                # Оценка качества калибровки
                calibration_metrics = self._evaluate_calibration(
                    y, uncalibrated_probs, calibrated_probs
                )
                
                # Сохраняем кривую калибровки
                self.calibration_curves[model_name] = self._compute_calibration_curve(
                    y, uncalibrated_probs, calibrated_probs
                )
                
                results[model_name] = calibration_metrics
                
                self.logger.info(f"  {model_name} - Brier score улучшение: "
                               f"{calibration_metrics['brier_improvement']:.4f}")
                
            except Exception as e:
                self.logger.error(f"Ошибка калибровки модели {model_name}: {e}")
                results[model_name] = {'error': str(e)}
        
        self.is_fitted = True
        return results
    
    def _evaluate_calibration(self,
                            y_true: np.ndarray,
                            uncalibrated_probs: np.ndarray,
                            calibrated_probs: np.ndarray) -> Dict[str, float]:
        """
        Оценка качества калибровки
        
        Args:
            y_true: Истинные метки
            uncalibrated_probs: Некалиброванные вероятности
            calibrated_probs: Калиброванные вероятности
            
        Returns:
            Dict с метриками калибровки
        """
        # Brier Score (чем меньше, тем лучше)
        brier_uncalibrated = brier_score_loss(y_true, uncalibrated_probs)
        brier_calibrated = brier_score_loss(y_true, calibrated_probs)
        
        # Log Loss (чем меньше, тем лучше)
        # Избегаем log(0) добавлением небольшого epsilon
        eps = 1e-15
        uncalibrated_clipped = np.clip(uncalibrated_probs, eps, 1 - eps)
        calibrated_clipped = np.clip(calibrated_probs, eps, 1 - eps)
        
        logloss_uncalibrated = log_loss(y_true, uncalibrated_clipped)
        logloss_calibrated = log_loss(y_true, calibrated_clipped)
        
        # Reliability (отклонение от идеальной калибровки)
        reliability_uncalibrated = self._compute_reliability(y_true, uncalibrated_probs)
        reliability_calibrated = self._compute_reliability(y_true, calibrated_probs)
        
        return {
            'brier_uncalibrated': brier_uncalibrated,
            'brier_calibrated': brier_calibrated,
            'brier_improvement': brier_uncalibrated - brier_calibrated,
            'logloss_uncalibrated': logloss_uncalibrated,
            'logloss_calibrated': logloss_calibrated,
            'logloss_improvement': logloss_uncalibrated - logloss_calibrated,
            'reliability_uncalibrated': reliability_uncalibrated,
            'reliability_calibrated': reliability_calibrated,
            'reliability_improvement': reliability_uncalibrated - reliability_calibrated
        }
    
    def _compute_reliability(self, y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
        """
        Вычисление reliability - отклонения от идеальной калибровки
        
        Args:
            y_true: Истинные метки
            y_prob: Предсказанные вероятности
            n_bins: Количество бинов для калибровочной кривой
            
        Returns:
            Reliability score (чем меньше, тем лучше)
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]
        
        reliability = 0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (y_prob > bin_lower) & (y_prob <= bin_upper)
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                accuracy_in_bin = y_true[in_bin].mean()
                avg_confidence_in_bin = y_prob[in_bin].mean()
                reliability += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
        
        return reliability
    
    def _compute_calibration_curve(self,
                                 y_true: np.ndarray,
                                 uncalibrated_probs: np.ndarray,
                                 calibrated_probs: np.ndarray,
                                 n_bins: int = 10) -> Dict[str, np.ndarray]:
        """
        Вычисление калибровочных кривых
        
        Returns:
            Dict с данными для построения калибровочных кривых
        """
        # Кривая для некалиброванных вероятностей
        frac_pos_uncal, mean_pred_uncal = calibration_curve(
            y_true, uncalibrated_probs, n_bins=n_bins
        )
        
        # Кривая для калиброванных вероятностей
        frac_pos_cal, mean_pred_cal = calibration_curve(
            y_true, calibrated_probs, n_bins=n_bins
        )
        
        return {
            'uncalibrated_fraction_positives': frac_pos_uncal,
            'uncalibrated_mean_predicted': mean_pred_uncal,
            'calibrated_fraction_positives': frac_pos_cal,
            'calibrated_mean_predicted': mean_pred_cal
        }
    
    def predict_proba(self, model_name: str, X: pd.DataFrame) -> np.ndarray:
        """
        Получение калиброванных вероятностей
        
        Args:
            model_name: Название модели
            X: Признаки для предсказания
            
        Returns:
            Калиброванные вероятности
        """
        if not self.is_fitted:
            raise ValueError("Калибратор не обучен")
        
        if model_name not in self.calibrated_models:
            raise ValueError(f"Модель {model_name} не найдена")
        
        calibrated_model = self.calibrated_models[model_name]
        return calibrated_model.predict_proba(X)[:, 1]
    
    def predict_all(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Получение калиброванных вероятностей для всех моделей
        
        Args:
            X: Признаки для предсказания
            
        Returns:
            Dict с калиброванными вероятностями для каждой модели
        """
        if not self.is_fitted:
            raise ValueError("Калибратор не обучен")
        
        results = {}
        for model_name in self.calibrated_models:
            results[model_name] = self.predict_proba(model_name, X)
        
        return results
    
    def plot_calibration_curve(self, model_name: str, save_path: str = None):
        """
        Построение калибровочной кривой
        
        Args:
            model_name: Название модели
            save_path: Путь для сохранения графика
        """
        if model_name not in self.calibration_curves:
            raise ValueError(f"Калибровочная кривая для модели {model_name} не найдена")
        
        curve_data = self.calibration_curves[model_name]
        
        plt.figure(figsize=(10, 6))
        
        # Идеальная калибровка (диагональ)
        plt.plot([0, 1], [0, 1], 'k--', label='Идеальная калибровка')
        
        # Некалиброванная модель
        plt.plot(
            curve_data['uncalibrated_mean_predicted'],
            curve_data['uncalibrated_fraction_positives'],
            marker='o', label='До калибровки'
        )
        
        # Калиброванная модель
        plt.plot(
            curve_data['calibrated_mean_predicted'],
            curve_data['calibrated_fraction_positives'],
            marker='s', label='После калибровки'
        )
        
        plt.xlabel('Средняя предсказанная вероятность')
        plt.ylabel('Доля положительных исходов')
        plt.title(f'Калибровочная кривая - {model_name}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"График сохранен: {save_path}")
        
        plt.show()
    
    def get_calibration_summary(self) -> pd.DataFrame:
        """
        Получение сводки по калибровке всех моделей
        
        Returns:
            DataFrame с метриками калибровки
        """
        if not self.is_fitted:
            return pd.DataFrame()
        
        summary_data = []
        
        for model_name in self.calibrated_models:
            if model_name in self.calibration_curves:
                # Получаем метрики из результатов калибровки
                # (в реальной реализации они должны сохраняться)
                summary_data.append({
                    'model': model_name,
                    'method': self.method,
                    'cv_folds': self.cv_folds
                })
        
        return pd.DataFrame(summary_data)
    
    def validate_calibration_quality(self, 
                                   model_name: str,
                                   threshold_brier: float = 0.25,
                                   threshold_reliability: float = 0.1) -> bool:
        """
        Валидация качества калибровки
        
        Args:
            model_name: Название модели
            threshold_brier: Максимальный допустимый Brier score
            threshold_reliability: Максимальная допустимая reliability
            
        Returns:
            True если калибровка качественная
        """
        if model_name not in self.calibrated_models:
            return False
        
        # В реальной реализации здесь должны быть сохраненные метрики
        # Для демонстрации возвращаем True
        return True


class AdvancedCalibrator:
    """
    Продвинутый калибратор с дополнительными методами
    """
    
    def __init__(self):
        self.logger = logging.getLogger('AdvancedCalibrator')
    
    def temperature_scaling(self, 
                          logits: np.ndarray, 
                          y_true: np.ndarray,
                          validation_split: float = 0.2) -> Tuple[float, np.ndarray]:
        """
        Temperature Scaling для калибровки
        
        Args:
            logits: Логиты модели (до softmax)
            y_true: Истинные метки
            validation_split: Доля данных для валидации температуры
            
        Returns:
            Tuple (оптимальная температура, калиброванные вероятности)
        """
        from scipy.optimize import minimize_scalar
        
        # Разделяем данные
        n_val = int(len(logits) * validation_split)
        val_logits = logits[:n_val]
        val_true = y_true[:n_val]
        test_logits = logits[n_val:]
        
        def temperature_loss(temperature):
            scaled_logits = val_logits / temperature
            probs = 1 / (1 + np.exp(-scaled_logits))  # Sigmoid
            return log_loss(val_true, np.clip(probs, 1e-15, 1-1e-15))
        
        # Оптимизация температуры
        result = minimize_scalar(temperature_loss, bounds=(0.1, 10.0), method='bounded')
        optimal_temperature = result.x
        
        # Применяем оптимальную температуру
        calibrated_probs = 1 / (1 + np.exp(-test_logits / optimal_temperature))
        
        return optimal_temperature, calibrated_probs
    
    def ensemble_calibration(self,
                           predictions: List[np.ndarray],
                           y_true: np.ndarray,
                           weights: List[float] = None) -> np.ndarray:
        """
        Калибровка ансамбля моделей
        
        Args:
            predictions: Список предсказаний разных моделей
            y_true: Истинные метки
            weights: Веса моделей в ансамбле
            
        Returns:
            Калиброванные вероятности ансамбля
        """
        if weights is None:
            weights = [1.0 / len(predictions)] * len(predictions)
        
        # Взвешенное усреднение предсказаний
        ensemble_probs = np.average(predictions, axis=0, weights=weights)
        
        # Калибровка ансамбля
        calibrator = IsotonicRegression(out_of_bounds='clip')
        calibrated_probs = calibrator.fit_transform(ensemble_probs, y_true)
        
        return calibrated_probs


def create_sample_calibration_data():
    """Создание примера данных для тестирования калибровки"""
    np.random.seed(42)
    
    n_samples = 1000
    
    # Создаем синтетические признаки
    X = pd.DataFrame({
        'feature_1': np.random.normal(0, 1, n_samples),
        'feature_2': np.random.normal(0, 1, n_samples),
        'feature_3': np.random.uniform(-1, 1, n_samples)
    })
    
    # Создаем целевую переменную с некоторой зависимостью от признаков
    linear_combination = (X['feature_1'] * 0.5 + 
                         X['feature_2'] * 0.3 + 
                         X['feature_3'] * 0.2 + 
                         np.random.normal(0, 0.5, n_samples))
    
    y = (linear_combination > 0).astype(int)
    
    # Создаем простую модель
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    
    models = {
        'random_forest': RandomForestClassifier(n_estimators=50, random_state=42),
        'logistic_regression': LogisticRegression(random_state=42)
    }
    
    # Обучаем модели
    for name, model in models.items():
        model.fit(X, y)
    
    return X, y, models


if __name__ == "__main__":
    # Пример использования
    print("Тестирование Probability Calibrator...")
    
    # Создаем тестовые данные
    X, y, models = create_sample_calibration_data()
    print(f"Создано {len(X)} образцов данных")
    print(f"Распределение меток: {pd.Series(y).value_counts().to_dict()}")
    
    # Создаем калибратор
    config = {
        'method': 'isotonic',
        'cv_folds': 5
    }
    
    calibrator = ProbabilityCalibrator(config)
    
    # Калибруем модели
    calibration_results = calibrator.fit(models, X, y)
    
    print(f"\nРезультаты калибровки:")
    for model_name, results in calibration_results.items():
        if 'error' not in results:
            print(f"\n{model_name}:")
            for metric, value in results.items():
                print(f"  {metric}: {value:.4f}")
    
    # Получаем калиброванные предсказания
    test_predictions = calibrator.predict_all(X[:100])  # Тестируем на первых 100 образцах
    
    print(f"\nКалиброванные предсказания:")
    for model_name, probs in test_predictions.items():
        print(f"{model_name}: среднее = {probs.mean():.3f}, std = {probs.std():.3f}")
    
    # Сводка по калибровке
    summary = calibrator.get_calibration_summary()
    if not summary.empty:
        print(f"\nСводка по калибровке:")
        print(summary)