#!/usr/bin/env python3
"""
ML Bridge Monitor - Утилита для мониторинга работы ML Bridge
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any

# Пути к файлам (должны совпадать с ml_bridge.py)
STATS_FILE = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ml_bridge_stats.json"
LOG_FILE = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ml_bridge.log"
PRED_FILE = r"C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\prediction_bt.txt"

class MLBridgeMonitor:
    """Класс для мониторинга ML Bridge"""
    
    def __init__(self):
        self.stats_file = STATS_FILE
        self.log_file = LOG_FILE
        self.pred_file = PRED_FILE
    
    def load_stats(self) -> Dict[str, Any]:
        """Загрузка статистики из файла"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"Ошибка загрузки статистики: {e}")
            return {}
    
    def get_log_tail(self, lines: int = 10) -> list:
        """Получение последних строк лога"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return all_lines[-lines:] if len(all_lines) >= lines else all_lines
            else:
                return []
        except Exception as e:
            print(f"Ошибка чтения лога: {e}")
            return []
    
    def get_last_prediction(self) -> str:
        """Получение последнего предсказания"""
        try:
            if os.path.exists(self.pred_file):
                with open(self.pred_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    return content if content else "Нет данных"
            else:
                return "Файл не найден"
        except Exception as e:
            return f"Ошибка чтения: {e}"
    
    def print_status(self):
        """Вывод текущего статуса"""
        print("=" * 70)
        print("ML BRIDGE MONITOR")
        print("=" * 70)
        
        # Статистика
        stats = self.load_stats()
        if stats:
            print("📊 СТАТИСТИКА:")
            print(f"   Всего сигналов: {stats.get('total_signals', 0)}")
            print(f"   BUY: {stats.get('buy_signals', 0)} | SELL: {stats.get('sell_signals', 0)} | NONE: {stats.get('none_signals', 0)}")
            print(f"   Ошибки - Чтение: {stats.get('read_errors', 0)}, Запись: {stats.get('write_errors', 0)}, Парсинг: {stats.get('parse_errors', 0)}")
            print(f"   Последний сигнал: {stats.get('last_signal_type', 'N/A')} в {stats.get('last_signal_time', 'N/A')}")
            print(f"   Время запуска: {stats.get('start_time', 'N/A')}")
        else:
            print("📊 СТАТИСТИКА: Данные недоступны")
        
        print()
        
        # Последнее предсказание
        print("🎯 ПОСЛЕДНЕЕ ПРЕДСКАЗАНИЕ:")
        last_pred = self.get_last_prediction()
        print(f"   {last_pred}")
        
        print()
        
        # Последние записи в логе
        print("📝 ПОСЛЕДНИЕ ЗАПИСИ В ЛОГЕ:")
        log_lines = self.get_log_tail(5)
        for line in log_lines:
            print(f"   {line.strip()}")
        
        print("=" * 70)
    
    def monitor_loop(self, interval: int = 30):
        """Цикл мониторинга с заданным интервалом"""
        print(f"Запуск мониторинга с интервалом {interval} секунд...")
        print("Нажмите Ctrl+C для выхода")
        
        try:
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')  # Очистка экрана
                self.print_status()
                print(f"\nСледующее обновление через {interval} секунд...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nМониторинг остановлен пользователем")

def main():
    """Основная функция"""
    monitor = MLBridgeMonitor()
    
    print("ML Bridge Monitor")
    print("1. Показать текущий статус")
    print("2. Запустить мониторинг")
    print("3. Выход")
    
    while True:
        choice = input("\nВыберите опцию (1-3): ").strip()
        
        if choice == '1':
            monitor.print_status()
        elif choice == '2':
            interval = input("Введите интервал обновления в секундах (по умолчанию 30): ").strip()
            try:
                interval = int(interval) if interval else 30
                monitor.monitor_loop(interval)
            except ValueError:
                print("Неверный формат интервала")
        elif choice == '3':
            print("До свидания!")
            break
        else:
            print("Неверный выбор")

if __name__ == "__main__":
    main()