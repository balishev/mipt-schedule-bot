#!/usr/bin/env python3
"""
Ежечасный обновлятель расписаний для запуска через cron
Запускает скачивание и парсинг расписаний каждый час с 7:00 до 23:00
"""

import subprocess
import logging
import sys
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hourly_updater.log', encoding='utf-8'),
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
    """Основная функция для ежечасного запуска"""
    now = datetime.now()
    current_hour = now.hour
    
    # Проверяем, находится ли текущее время в рабочем интервале (7:00 - 23:00)
    if current_hour < 7 or current_hour >= 23:
        logger.info(f"Текущее время {current_hour}:00 - вне рабочего интервала (7:00-23:00), пропускаем обновление")
        return
    
    logger.info(f"=== Запуск обновления в {current_hour}:00 ===")
    
    if run_download():
        if run_parser():
            logger.info("Расписание успешно обновлено!")
        else:
            logger.warning("Парсинг не удался, но скачивание прошло успешно")
    else:
        logger.error("Скачивание не удалось, пропускаем парсинг")

if __name__ == "__main__":
    main()