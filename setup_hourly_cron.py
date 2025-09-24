#!/usr/bin/env python3
"""
Настройка cron для ежечасного обновления расписаний с 7:00 до 23:00
"""

import subprocess
import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cron_setup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_cron_jobs():
    """Настраивает cron задания для ежечасного обновления"""
    try:
        # Получаем текущие cron задания
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_cron = result.stdout if result.returncode == 0 else ""
        
        # Удаляем старые задания нашего скрипта
        lines = current_cron.split('\n')
        new_lines = [line for line in lines if 'hourly_schedule_updater.py' not in line]
        
        # Добавляем новые задания для каждого часа с 7:00 до 23:00
        cron_entries = []
        for hour in range(7, 23):  # с 7:00 до 22:59
            cron_entry = f"0 {hour} * * * cd {os.getcwd()} && {sys.executable} hourly_schedule_updater.py >> hourly_cron.log 2>&1"
            cron_entries.append(cron_entry)
        
        # Объединяем старые и новые задания
        all_entries = new_lines + cron_entries
        
        # Создаем временный файл с новыми заданиями
        with open('temp_cron', 'w') as f:
            f.write('\n'.join(all_entries))
            f.write('\n')
        
        # Устанавливаем новые cron задания
        subprocess.run(['crontab', 'temp_cron'], check=True)
        os.remove('temp_cron')
        
        logger.info("Cron задания успешно настроены!")
        logger.info(f"Добавлено заданий: {len(cron_entries)} (с 7:00 до 23:00 каждый час)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при настройке cron: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return False

def show_current_cron():
    """Показывает текущие cron задания"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Текущие cron задания:")
            logger.info(result.stdout)
        else:
            logger.info("Cron задания не настроены")
    except Exception as e:
        logger.error(f"Ошибка при просмотре cron: {e}")

def main():
    """Основная функция"""
    logger.info("=== Настройка ежечасного обновления расписаний ===")
    
    # Показываем текущие задания
    show_current_cron()
    
    # Настраиваем новые задания
    if setup_cron_jobs():
        logger.info("\nНовые cron задания настроены успешно!")
        logger.info("Расписание будет обновляться каждый час с 7:00 до 23:00")
        
        # Показываем обновленные задания
        show_current_cron()
    else:
        logger.error("Не удалось настроить cron задания")

if __name__ == "__main__":
    main()