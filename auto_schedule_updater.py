#!/usr/bin/env python3
"""
Автоматический обновлятель расписаний
Запускает скачивание и парсинг расписаний с заданным интервалом
"""

import subprocess
import time
import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_updater.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_download():
    """Запускает скачивание расписаний"""
    try:
        result = subprocess.run(
            [sys.executable, 'weekly_schedule_downloader.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 минут таймаут
        )
        if result.returncode == 0:
            logger.info("Скачивание завершено успешно")
            return True
        else:
            logger.error(f"Ошибка при скачивании: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Таймаут при скачивании расписаний")
        return False
    except Exception as e:
        logger.error(f"Исключение при скачивании: {e}")
        return False

def run_parser():
    """Запускает парсинг расписаний"""
    try:
        result = subprocess.run(
            [sys.executable, 'multi_file_parser.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 минут таймаут
        )
        if result.returncode == 0:
            logger.info("Парсинг завершен успешно")
            return True
        else:
            logger.error(f"Ошибка при парсинге: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Таймаут при парсинге расписаний")
        return False
    except Exception as e:
        logger.error(f"Исключение при парсинге: {e}")
        return False

def main():
    """Основная функция с циклом обновления"""
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            logger.error("Интервал должен быть числом (секунды)")
            return
    else:
        interval = 15  # секунд по умолчанию
    
    logger.info(f"Запуск автоматического обновления расписания с интервалом {interval} секунд")
    
    iteration = 0
    max_iterations = 4  # Ограничим тест 4 итерациями
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"=== Итерация {iteration} ===")
        
        if run_download():
            if run_parser():
                logger.info("Расписание успешно обновлено!")
            else:
                logger.warning("Парсинг не удался, но скачивание прошло успешно")
        else:
            logger.error("Скачивание не удалось, пропускаем парсинг")
        
        if iteration < max_iterations:
            logger.info(f"Ожидание {interval} секунд до следующего обновления...")
            time.sleep(interval)
    
    logger.info("Тестовый цикл завершен. Для постоянной работы увеличьте max_iterations.")

if __name__ == "__main__":
    main()