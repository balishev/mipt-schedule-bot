#!/usr/bin/env python3
"""
Ежедневный обновлятель расписаний с 7:00 до 23:00 каждый час
Запускает скачивание и парсинг расписаний по расписанию
"""

import subprocess
import time
import logging
import sys
import os
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_updater.log', encoding='utf-8'),
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

def should_run_update(last_update_hour):
    """Определяет, нужно ли запускать обновление в текущее время"""
    now = datetime.now()
    current_hour = now.hour
    
    # Проверяем, находится ли текущее время в рабочем интервале (7:00 - 23:00)
    if current_hour < 7 or current_hour >= 23:
        logger.debug(f"Текущее время {current_hour}:00 - вне рабочего интервала (7:00-23:00)")
        return False
    
    # Проверяем, не обновлялись ли мы уже в этот час
    if last_update_hour == current_hour:
        logger.debug(f"Уже обновлялись в {current_hour}:00")
        return False
    
    logger.info(f"Время для обновления: {current_hour}:00")
    return True

def main():
    """Основная функция с циклом обновления"""
    logger.info("Запуск ежедневного обновления расписания (7:00-23:00 каждый час)")
    
    last_update_hour = -1  # Инициализируем значением, которого не может быть в часах
    
    while True:
        now = datetime.now()
        current_hour = now.hour
        
        if should_run_update(last_update_hour):
            logger.info(f"=== Запуск обновления в {current_hour}:00 ===")
            
            if run_download():
                if run_parser():
                    logger.info("Расписание успешно обновлено!")
                    last_update_hour = current_hour  # Запоминаем час последнего обновления
                else:
                    logger.warning("Парсинг не удался, но скачивание прошло успешно")
            else:
                logger.error("Скачивание не удалось, пропускаем парсинг")
        
        # Ждем 1 минуту перед следующей проверкой
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Обновление остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")