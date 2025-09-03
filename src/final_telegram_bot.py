import json
import logging
import re
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Добавляем корневую директорию в путь для импорта config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config
except ImportError:
    # Создаем пустой config модуль для совместимости
    class Config:
        BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
        DEBUG = False
        LOG_LEVEL = "INFO"
    
    config = Config()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка данных расписания и структуры
def load_schedule_data():
    try:
        with open('data/correct_schedules.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading schedule data: {e}")
        return {}

def load_registration_structure():
    try:
        with open('data/registration_structure.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading registration structure: {e}")
        return {}

schedule_data = load_schedule_data()
registration_structure = load_registration_structure()

# Хранение пользовательских данных
user_data = {}

# Функции для улучшения интерфейса
def format_time(time_str):
    """Форматирование времени из '1355 - 1520' в '13:55 - 15:20'"""
    try:
        if ' - ' in time_str:
            start, end = time_str.split(' - ')
            if len(start) == 4 and start.isdigit():
                start = f"{start[:2]}:{start[2:]}"
            if len(end) == 4 and end.isdigit():
                end = f"{end[:2]}:{end[2:]}"
            return f"{start} - {end}"
        return time_str
    except:
        return time_str

def get_file_key_from_group(group_name, level, course, faculty_short):
    """Получение file_key для группы на основе структуры"""
    try:
        if level in registration_structure and course in registration_structure[level]:
            for faculty, data in registration_structure[level][course].items():
                if faculty == faculty_short and group_name in data['groups']:
                    # Создаем уникальный идентификатор для файла
                    return f"{level}_{course}_{faculty}"
        return f"{level}_{course}"
    except:
        return f"{level}_{course}"

def find_group_schedule(group_name, level, course):
    """Поиск расписания для группы в данных"""
    try:
        logger.info(f"Searching schedule for group: {group_name}, level: {level}, course: {course}")
        
        # Формируем ключ для поиска в schedule_data
        file_key = f"{level} {course} КУРС ОСЕНЬ 2025-2026 г"
        logger.info(f"Looking for file key: {file_key}")
        
        if file_key in schedule_data:
            logger.info(f"Found file key: {file_key}")
            course_data = schedule_data[file_key]
            
            # Проверяем, существует ли группа в списке групп
            group_exists = False
            if 'groups' in course_data and group_name in course_data['groups'].values():
                logger.info(f"Group {group_name} exists in groups list")
                group_exists = True
            
            # Если группа существует, возвращаем все расписание курса
            if group_exists:
                logger.info(f"Returning full course schedule for {group_name}")
                return course_data
            
            # Дополнительная проверка: ищем группу в расписании по дням
            if 'schedule' in course_data:
                logger.info(f"Schedule found for {file_key}, searching for group in schedule")
                for day_name, day_data in course_data['schedule'].items():
                    logger.info(f"Checking day: {day_name}")
                    for faculty_name, faculty_groups in day_data.items():
                        logger.info(f"Checking faculty: {faculty_name}")
                        if group_name in faculty_groups:
                            logger.info(f"Found group {group_name} in faculty {faculty_name} on day {day_name}")
                            # Группа найдена в расписании, возвращаем все расписание курса
                            return course_data
            else:
                logger.info(f"No 'schedule' key found in {file_key}")
            
            logger.info(f"Group {group_name} not found in schedule or groups list")
        else:
            logger.info(f"File key {file_key} not found in schedule_data")
            logger.info(f"Available keys: {list(schedule_data.keys())}")
        
        return None
    except Exception as e:
        logger.error(f"Error finding schedule for group {group_name}: {e}")
        return None

def format_schedule_for_day(group_schedule, day_name, group_name):
    """Форматирование расписания на день для отображения"""
    try:
        logger.info(f"Formatting schedule for group {group_name}, day {day_name}")
        
        if not group_schedule:
            logger.warning(f"No schedule data found for group {group_name}")
            return ("📭 Расписание не найдено для этой группы\n\n"
                   "ℹ️ *Возможные причины:*\n"
                   "• Расписание для вашего курса еще не загружено\n"
                   "• Проверьте другие дни недели\n"
                   "• Обратитесь к администратору для обновления данных")
        
        # Если получили данные всего курса
        if 'schedule' in group_schedule:
            logger.info(f"Found course schedule data, looking for day {day_name}")
            if day_name in group_schedule['schedule']:
                day_data = group_schedule['schedule'][day_name]
                logger.info(f"Found day {day_name} in schedule")
                
                # Ищем группу в данных дня
                for faculty_name, faculty_groups in day_data.items():
                    logger.info(f"Checking faculty {faculty_name} for group {group_name}")
                    if group_name in faculty_groups:
                        logger.info(f"Found group {group_name} in faculty {faculty_name}")
                        lessons = faculty_groups[group_name]
                        result = f"📅 *Расписание на {day_name}:*\n\n"
                        
                        if lessons:
                            logger.info(f"Found {len(lessons)} lessons for {group_name}")
                            for lesson in lessons:
                                time_formatted = format_time(lesson['time'])
                                subject = lesson.get('subject', 'Не указано')
                                classroom = lesson.get('classroom', 'Не указано')
                                teacher = lesson.get('teacher', 'Не указано')
                                
                                result += f"⏰ *{time_formatted}*\n"
                                result += f"📚 {subject}\n"
                                if classroom and classroom != 'Не указано':
                                    result += f"🏫 Аудитория: {classroom}\n"
                                if teacher and teacher != 'Не указано':
                                    result += f"👨‍🏫 Преподаватель: {teacher}\n"
                                result += "---\n"
                        else:
                            logger.info(f"No lessons found for {group_name} on {day_name}")
                            result += f"📭 На {day_name} занятий нет\n\n"
                            result += "ℹ️ Расписание может быть доступно для других дней недели"
                        
                        return result
                else:
                    logger.info(f"Group {group_name} not found in any faculty for day {day_name}")
            else:
                logger.warning(f"Day {day_name} not found in schedule")
            
            # Если группа не найдена в конкретном дне, но существует в курсе
            if 'groups' in group_schedule and group_name in group_schedule['groups'].values():
                logger.info(f"Group {group_name} exists in course but no lessons found for {day_name}")
                return (f"📭 На {day_name} занятий не найдено\n\n"
                       "ℹ️ *Возможные причины:*\n"
                       "• Для вашей группы нет занятий в этот день\n"
                       "• Расписание может быть доступно для других дней\n"
                       "• Проверьте другие дни недели")
            else:
                logger.warning(f"Group {group_name} not found in course groups")
                return (f"📭 На {day_name} занятий не найдено\n\n"
                       "ℹ️ *Возможные причины:*\n"
                       "• Группа не найдена в расписании\n"
                       "• Проверьте правильность выбранной группы\n"
                       "• Обратитесь к администратору")
        
        else:
            logger.warning(f"Unknown schedule data structure: {group_schedule}")
            return ("📭 Расписание не найдено\n\n"
                   "ℹ️ *Возможные причины:*\n"
                   "• Расписание для вашего курса еще не загружено\n"
                   "• Обратитесь к администратору для обновления данных")
            
    except Exception as e:
        logger.error(f"Error formatting schedule: {e}")
        return "❌ Ошибка при формировании расписания"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начальная команда"""
    keyboard = [
        [InlineKeyboardButton("🎓 Регистрация", callback_data='register')],
        [InlineKeyboardButton("📅 Посмотреть расписание", callback_data='view_schedule')],
        [InlineKeyboardButton("ℹ️ Информация", callback_data='info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎓 *Добро пожаловать в бот расписания МФТИ!*\n\n"
        "Этот бот поможет вам быстро найти расписание занятий для вашей группы.\n\n"
        "📋 *Доступные функции:*\n"
        "• Регистрация с выбором уровня, курса, факультета и группы\n"
        "• Просмотр расписания по дням недели\n"
        "• Быстрый доступ к информации о занятиях\n\n"
        "Выберите действие:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Регистрация пользователя - выбор уровня обучения"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎓 Бакалавриат", callback_data='level_бакалавриат')],
        [InlineKeyboardButton("🎓 Магистратура", callback_data='level_магистратура')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎓 *Выберите уровень обучения:*\n\n"
        "Нажмите на соответствующую кнопку ниже:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def select_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор уровня обучения (бакалавриат/магистратура)"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    level = query.data.replace('level_', '')
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['level'] = level
    
    keyboard = []
    if level in registration_structure:
        for course in registration_structure[level].keys():
            # Подсчитываем общее количество групп для этого курса
            total_groups = 0
            for faculty_data in registration_structure[level][course].values():
                total_groups += len(faculty_data['groups'])
            
            button_text = f"Курс {course} ({total_groups} групп)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'course_{course}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='register')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    level_name = "Бакалавриат" if level == "бакалавриат" else "Магистратура"
    
    await query.edit_message_text(
        f"🎓 *Уровень: {level_name}*\n\n"
        "Выберите ваш курс:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор курса"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    course = query.data.replace('course_', '')
    level = user_data[user_id]['level']
    
    user_data[user_id]['course'] = course
    
    keyboard = []
    if level in registration_structure and course in registration_structure[level]:
        for faculty_short, faculty_data in registration_structure[level][course].items():
            groups_count = len(faculty_data['groups'])
            faculty_name = faculty_data['full_name']
            button_text = f"{faculty_short} ({groups_count} групп)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'faculty_{faculty_short}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f'level_{level}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    level_name = "Бакалавриат" if level == "бакалавриат" else "Магистратура"
    
    await query.edit_message_text(
        f"🎓 *Уровень:* {level_name}\n"
        f"📚 *Курс:* {course}\n\n"
        "Выберите ваш факультет:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def select_faculty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор факультета"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Определяем, это новый выбор факультета или пагинация
    if query.data.startswith('faculty_'):
        faculty_short = query.data.replace('faculty_', '')
        level = user_data[user_id]['level']
        course = user_data[user_id]['course']
        
        user_data[user_id]['faculty'] = faculty_short
        # Сбрасываем страницу при выборе нового факультета
        context.user_data['group_page'] = 0
    else:
        # Используем сохраненные данные для пагинации
        level = user_data[user_id]['level']
        course = user_data[user_id]['course']
        faculty_short = user_data[user_id]['faculty']
    
    keyboard = []
    if (level in registration_structure and
        course in registration_structure[level] and
        faculty_short in registration_structure[level][course]):
        
        groups = registration_structure[level][course][faculty_short]['groups']
        
        # Показываем группы с пагинации (по 10 групп на страницу)
        current_page = context.user_data.get('group_page', 0)
        groups_per_page = 10
        start_idx = current_page * groups_per_page
        end_idx = start_idx + groups_per_page
        
        # Отображаем информацию о странице
        page_info = f"Страница {current_page + 1}/{(len(groups) + groups_per_page - 1) // groups_per_page}"
        
        for group in groups[start_idx:end_idx]:
            keyboard.append([InlineKeyboardButton(f"📚 {group}", callback_data=f'group_{group}')])
        
        # Добавляем кнопки навигации
        nav_buttons = []
        if current_page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data='group_prev_page'))
        
        # Информация о странице
        if len(groups) > groups_per_page:
            nav_buttons.append(InlineKeyboardButton(f"📄 {page_info}", callback_data='page_info'))
        
        if end_idx < len(groups):
            nav_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data='group_next_page'))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔍 Поиск группы", callback_data='search_in_groups')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f'course_{course}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    level_name = "Бакалавриат" if level == "бакалавриат" else "Магистратура"
    faculty_full = registration_structure[level][course][faculty_short]['full_name']
    
    await query.edit_message_text(
        f"🎓 *Уровень:* {level_name}\n"
        f"📚 *Курс:* {course}\n"
        f"🏫 *Факультет:* {faculty_short} ({faculty_full})\n\n"
        f"👥 *Группы:* {len(groups)} всего\n\n"
        "Выберите вашу группу:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_group_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка пагинации групп"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    current_page = context.user_data.get('group_page', 0)
    
    if action == 'group_next_page':
        context.user_data['group_page'] = current_page + 1
    elif action == 'group_prev_page':
        context.user_data['group_page'] = max(0, current_page - 1)
    
    # Повторно вызываем выбор факультета для обновления списка групп
    await select_faculty(update, context)

async def select_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выбор группы"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    group_name = query.data.replace('group_', '')
    
    user_data[user_id]['group'] = group_name
    
    # Формируем информацию о выбранном пути
    level = user_data[user_id]['level']
    course = user_data[user_id]['course']
    faculty_short = user_data[user_id]['faculty']
    
    level_name = "Бакалавриат" if level == "бакалавриат" else "Магистратура"
    faculty_full = registration_structure[level][course][faculty_short]['full_name']
    
    keyboard = [
        [InlineKeyboardButton("📅 Посмотреть расписание", callback_data='view_schedule')],
        [InlineKeyboardButton("🔄 Изменить регистрацию", callback_data='register')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    registration_text = (
        f"✅ Регистрация завершена!\n\n"
        f"🎓 Уровень: {level_name}\n"
        f"📚 Курс: {course}\n"
        f"🏫 Факультет: {faculty_short} ({faculty_full})\n"
        f"👥 Группа: {group_name}\n\n"
        "Теперь вы можете посмотреть расписание."
    )
    
    await query.edit_message_text(
        registration_text,
        reply_markup=reply_markup,
        parse_mode=None
    )

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просмотр расписания"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in user_data or 'level' not in user_data[user_id]:
        keyboard = [[InlineKeyboardButton("🎓 Зарегистрироваться", callback_data='register')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❗ *Необходима регистрация*\n\n"
            "Сначала необходимо зарегистрироваться и выбрать направление.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Дни недели для расписания
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    
    keyboard = []
    for day in days:
        keyboard.append([InlineKeyboardButton(f"📅 {day}", callback_data=f'day_{day}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем информацию о выбранном пути
    level = user_data[user_id]['level']
    course = user_data[user_id]['course']
    faculty_short = user_data[user_id].get('faculty', 'Не выбран')
    group = user_data[user_id].get('group', 'Не выбрана')
    
    level_name = "Бакалавриат" if level == "бакалавриат" else "Магистратура"
    
    selection_info = f"🎓 *Уровень:* {level_name}\n📚 *Курс:* {course}"
    
    if faculty_short != 'Не выбран':
        faculty_full = registration_structure[level][course][faculty_short]['full_name']
        selection_info += f"\n🏫 *Факультет:* {faculty_short} ({faculty_full})"
    
    selection_info += f"\n👥 *Группа:* {group}"
    
    await query.edit_message_text(
        f"📅 *Расписание*\n\n"
        f"{selection_info}\n\n"
        "Выберите день недели:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_day_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать расписание на день"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    day_name = query.data.replace('day_', '')
    
    if user_id not in user_data:
        await query.edit_message_text('❗ Ошибка: пользователь не зарегистрирован.')
        return
    
    # Формируем информацию о выбранном пути
    level = user_data[user_id]['level']
    course = user_data[user_id]['course']
    faculty_short = user_data[user_id].get('faculty', '')
    group = user_data[user_id].get('group', '')
    
    level_name = "Бакалавриат" if level == "бакалавриат" else "Магистратура"
    
    selection_info = f"🎓 *Уровень:* {level_name}\n📚 *Курс:* {course}"
    
    if faculty_short:
        faculty_full = registration_structure[level][course][faculty_short]['full_name']
        selection_info += f"\n🏫 *Факультет:* {faculty_short} ({faculty_full})"
    
    selection_info += f"\n👥 *Группа:* {group if group else 'Не выбрана'}"
    
    message = f"📅 *Расписание на {day_name}*\n"
    message += f"{selection_info}\n\n"
    
    # Получаем расписание для группы
    if group and group != 'Не выбрана':
        logger.info(f"Getting schedule for group: {group}, level: {level}, course: {course}, day: {day_name}")
        group_schedule = find_group_schedule(group, level, course)
        schedule_text = format_schedule_for_day(group_schedule, day_name, group)
        message += schedule_text
    else:
        message += "❌ Группа не выбрана. Сначала выберите группу в меню регистрации."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Выбрать другой день", callback_data='view_schedule')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Разбиваем сообщение на части, если оно слишком длинное
    if len(message) > 4000:
        parts = []
        current_part = ""
        lines = message.split('\n')
        
        for line in lines:
            if len(current_part) + len(line) + 1 < 4000:
                current_part += line + '\n'
            else:
                parts.append(current_part)
                current_part = line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        # Отправляем первую часть с клавиатурой
        await query.edit_message_text(parts[0], reply_markup=reply_markup, parse_mode='Markdown')
        
        # Отправляем остальные части как отдельные сообщения
        for part in parts[1:]:
            await context.bot.send_message(chat_id=query.message.chat_id, text=part, parse_mode='Markdown')
    else:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать информацию о боте"""
    query = update.callback_query
    await query.answer()
    
    info_text = (
        "ℹ️ *Информация о боте*\n\n"
        "🎓 *Бот расписания МФТИ*\n"
        "Версия: 2.0 (обновленная структура)\n\n"
        "📊 *Доступные данные:*\n"
    )
    
    # Подсчет общего количества групп
    total_groups = 0
    for level_data in registration_structure.values():
        for course_data in level_data.values():
            for faculty_data in course_data.values():
                total_groups += len(faculty_data['groups'])
    
    info_text += f"• Всего групп: {total_groups}\n"
    
    info_text += (
        "\n🔧 *Функции:*\n"
        "• Регистрация с выбором уровня, курса, факультета и группы\n"
        "• Просмотр расписания по дням\n"
        "• Улучшенный интерфейс с пагинацией\n\n"
        "📞 *Поддержка:* @your_support_username"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎓 Регистрация", callback_data='register')],
        [InlineKeyboardButton("📅 Посмотреть расписание", callback_data='view_schedule')],
        [InlineKeyboardButton("ℹ️ Информация", callback_data='info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏠 *Главное меню*\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_search_in_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка поиска группы в процессе регистрации"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Сохраняем контекст для возврата
    context.user_data['search_in_groups'] = True
    context.user_data['search_user_id'] = user_id
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к выбору группы", callback_data='back_to_groups')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔍 *Поиск группы*\n\n"
        "Введите номер или часть названия группы для поиска.\n"
        "Пример: '501', 'М05', '404'\n\n"
        "📝 *Просто введите текст сообщением:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Проверяем, находится ли пользователь в режиме поиска
    if context.user_data.get('search_in_groups') and context.user_data.get('search_user_id') == user_id:
        # Поиск в процессе регистрации
        level = user_data[user_id]['level']
        course = user_data[user_id]['course']
        faculty_short = user_data[user_id]['faculty']
        
        groups = registration_structure[level][course][faculty_short]['groups']
        
        results = []
        for group in groups:
            if message_text.lower() in group.lower():
                results.append(group)
        
        if results:
            keyboard = []
            for group in results[:10]:
                keyboard.append([InlineKeyboardButton(f"📚 {group}", callback_data=f'group_{group}')])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад к поиску", callback_data='search_in_groups')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🔍 *Результаты поиска для '{message_text}':*\n\n"
                f"Найдено: {len(results)} групп\n\n"
                "Выберите группу:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ По запросу '{message_text}' групп не найдено.\n\n"
                "Попробуйте другой запрос:",
                parse_mode='Markdown'
            )
    
    else:
        await update.message.reply_text(
            "🤖 Используйте команду /start для начала работы с ботом или кнопки в меню."
        )

def main() -> None:
    """Запуск бота"""
    # Токен бота из конфигурационного файла
    TOKEN = config.BOT_TOKEN
    
    if TOKEN == "YOUR_BOT_TOKEN_HERE" or not TOKEN:
        print("❗ ВНИМАНИЕ: Необходимо указать токен бота!")
        print("1. Скопируйте файл config.example.py в config.py")
        print("2. Замените 'YOUR_BOT_TOKEN_HERE' на ваш токен в config.py")
        print("3. Запустите бота снова")
        return
    
    # Настройка уровня логирования из конфига
    if hasattr(config, 'LOG_LEVEL'):
        logging.getLogger().setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(register, pattern='^register$'))
    application.add_handler(CallbackQueryHandler(select_level, pattern='^level_'))
    application.add_handler(CallbackQueryHandler(select_course, pattern='^course_'))
    application.add_handler(CallbackQueryHandler(select_faculty, pattern='^faculty_'))
    application.add_handler(CallbackQueryHandler(handle_group_pagination, pattern='^group_(next|prev)_page$'))
    application.add_handler(CallbackQueryHandler(select_group, pattern='^group_'))
    application.add_handler(CallbackQueryHandler(view_schedule, pattern='^view_schedule$'))
    application.add_handler(CallbackQueryHandler(show_day_schedule, pattern='^day_'))
    application.add_handler(CallbackQueryHandler(show_info, pattern='^info$'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(handle_search_in_groups, pattern='^search_in_groups$'))
    application.add_handler(CallbackQueryHandler(select_faculty, pattern='^back_to_groups$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    print("🤖 Бот запущен...")
    print("📊 Используется обновленная структура регистрации")
    print("🔍 Включено подробное логирование для отладки")
    
    application.run_polling()

if __name__ == '__main__':
    main()