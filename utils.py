import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup 
from telebot import types
from telebot.storage import StateMemoryStorage

from config import TOKEN, services_per_page, masters_per_page, days_per_page, start_hour, end_hour, bookings_per_page
from models import Admin, Master

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

class UserStates(StatesGroup):

    '''Class for defining states'''

    main_menu = State()
    admin_menu = State()
    master_menu = State()
    add_new_admin = State()
    manage_master_menu = State()
    add_master = State()
    add_master_2 = State()
    add_master_3 = State()
    edit_master = State()
    manage_service = State()
    edit_service = State()
    edit_service_title = State()
    edit_service_cost = State()
    add_service = State()
    change_master_schedule = State()

def create_masters_keyboard(masters, page, book, service_id):
    total_masters = len(masters)
    total_pages = total_masters // masters_per_page + (1 if total_masters % masters_per_page > 0 else 0)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * masters_per_page
    current_masters = masters[offset:offset + masters_per_page]

    keyboard = types.InlineKeyboardMarkup()
    if book:
        for master in current_masters:
            keyboard.add(types.InlineKeyboardButton(
                text=master['name'],
                callback_data=f'book_{master["id_master"]}_{service_id}'
            ))

    else:
        for master in current_masters:
            keyboard.add(types.InlineKeyboardButton(
                text=master['name'],
                callback_data=f'mast_{master["id_master"]}'
            ))


    # Додаємо кнопки пагінації
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='⬅️ Попередня',
                callback_data=f'mast_page_{page - 1}'
            ))
        if page < total_pages:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='➡️ Наступна',
                callback_data=f'mast_page_{page + 1}'
            ))
    if pagination_buttons:
        keyboard.row(*pagination_buttons)

    return keyboard

def send_masters(masters, message, service_id = None, page=1, previous_message=None, book = False):
    # Видаляємо попереднє повідомлення з майстрами, якщо таке є
    if previous_message != None:
        try:
            bot.delete_message(message.chat.id, previous_message.id)
        except Exception as e:
            print("Error while deleting message:", e)

    keyboard = create_masters_keyboard(masters, page, book, service_id)
    bot.send_message(message.chat.id, 'Виберіть майстра:', reply_markup=keyboard)

def create_services_keyboard(services, page, book, master_id):
    total_services = len(services)
    total_pages = total_services // services_per_page + (1 if total_services % services_per_page > 0 else 0)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * services_per_page
    current_services = services[offset:offset + services_per_page]

    keyboard = types.InlineKeyboardMarkup()


    if book:
        for service in current_services:
            keyboard.add(types.InlineKeyboardButton(
                text=service['title'],
                callback_data=f'book_{master_id}_{service["id_service"]}'
            ))
    else:
        for service in current_services:
            keyboard.add(types.InlineKeyboardButton(
                text=service['title'],
                callback_data=f'serv_{service["id_service"]}'
            ))

    # Додаємо кнопки пагінації
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='⬅️ Попередня',
                callback_data=f'serv_page_{page - 1}'
            ))
        if page < total_pages:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='➡️ Наступна',
                callback_data=f'serv_page_{page + 1}'
            ))
    if pagination_buttons:
        keyboard.row(*pagination_buttons)

    return keyboard

def send_services(services, message, master_id = None, page=1, previous_message=None, book = False):
    # Видаляємо попереднє повідомлення з майстрами, якщо таке є
    if previous_message != None:
        try:
            bot.delete_message(message.chat.id, previous_message.id)
        except Exception as e:
            print("Error while deleting message:", e)

    keyboard = create_services_keyboard(services, page, book, master_id)
    bot.send_message(message.chat.id, 'Виберіть сервіс:', reply_markup=keyboard)

def create_days_keyboard(days, page, change_schedule):
    total_days = len(days)
    total_pages = total_days // days_per_page + (1 if total_days % days_per_page > 0 else 0)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * days_per_page
    current_days = days[offset:offset + days_per_page]

    keyboard = types.InlineKeyboardMarkup()

    if not change_schedule:
        for day in current_days:
            keyboard.add(types.InlineKeyboardButton(
                text=day,
                callback_data=f'bookday_{day}'
            ))
    elif change_schedule:
        for day in current_days:
            keyboard.add(types.InlineKeyboardButton(
                text=day,
                callback_data=f'change_schedule_day_{day}'
            ))

    # Додаємо кнопки пагінації
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='⬅️ Попередня',
                callback_data=f'day_page_{page - 1}'
            ))
        if page < total_pages:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='➡️ Наступна',
                callback_data=f'day_page_{page + 1}'
            ))
    if pagination_buttons:
        keyboard.row(*pagination_buttons)

    return keyboard

def send_days(days, message, page=1, previous_message=None, change_schedule = False):
    # Видаляємо попереднє повідомлення з майстрами, якщо таке є
    if previous_message != None:
        try:
            bot.delete_message(message.chat.id, previous_message.id)
        except Exception as e:
            print("Error while deleting message:", e)

    keyboard = create_days_keyboard(days, page, change_schedule)
    bot.send_message(message.chat.id, 'Виберіть день:', reply_markup=keyboard)

def create_working_hours_keyboard(chosen_hours=None):
    """
    Створює інлайн клавіатуру з робочими годинами та кнопкою "Готово".

    :param chosen_hour: Обрана година (якщо є).
    :return: Інлайн клавіатура з робочими годинами.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    for hour in range(start_hour, end_hour):
        button_text = f"{hour}:00"
        if chosen_hours is not None and hour in chosen_hours:
            button_text += " ✅"
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=f"hour_{hour}"))
    keyboard.add(types.InlineKeyboardButton(text="Готово", callback_data="add_master"))
    return keyboard

def create_schedule_keyboard(booked_slots, break_slots, available_slots):
    """
    Створює інлайн клавіатуру з робочими годинами та позначенням стану годин.

    :param booked_slots: Список заброньованих годин.
    :param break_slots: Список годин перерви.
    :param available_slots: Список доступних годин.
    :return: Інлайн клавіатура з робочими годинами та позначенням стану годин.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    for hour in range(start_hour, end_hour):
        hour_str = str(hour).zfill(2) + ":00"
        button_text = f"{hour_str}"
        # Додаємо смайлик із замочком на заброньовані години
        if hour_str in booked_slots:
            button_text += " 🔒"
        # Додаємо галочку на доступні години
        elif hour_str in available_slots:
            button_text += " ✅"
        # Додаємо червоний хрестик на години перерви
        elif hour_str in break_slots:
            button_text += " ❌"
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=f"change_hour_{hour}"))
    keyboard.add(types.InlineKeyboardButton(text="Готово", callback_data="change_schedule"))
    return keyboard

def set_working_hours(chosen_hours):
    working_hours = {}
    for hour in range(start_hour, end_hour):
        time_str = f"{hour:02}:00"
        if hour in chosen_hours:
            working_hours[time_str] = 'available'
        else:
            working_hours[time_str] = 'break'
    return working_hours

def create_main_menu_keyboard(chat_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    working_hours_button = types.KeyboardButton('Коли ви працюєте?')
    available_serv = types.KeyboardButton(text='Доступні послуги')
    available_master = types.KeyboardButton(text='Перегляд майстрів')
    my_book = types.KeyboardButton(text='Мої записи')

    if Admin.is_admin(chat_id):
        admin_baton = types.KeyboardButton(text="Кнопка влади")
        keyboard.add(admin_baton)

    if Master.is_master(chat_id):
        master_baton = types.KeyboardButton(text="Кнопка Шифу")
        keyboard.add(master_baton)

    # Додаємо решту кнопок до клавіатури
    keyboard.add(working_hours_button, available_serv, available_master, my_book)

    return keyboard

def create_service_keyboard_to_combine(services, page, chosen_services_ids):
    total_services = len(services)
    total_pages = total_services // services_per_page + (1 if total_services % services_per_page > 0 else 0)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * services_per_page
    current_services = services[offset:offset + services_per_page]

    keyboard = types.InlineKeyboardMarkup()

    for service in current_services:
        button_text = service['title']
        if chosen_services_ids is not None and service['id_service'] in chosen_services_ids:
            button_text += " ✅"
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=f'combine_serv_{service["id_service"]}'))

    # Додаємо кнопки пагінації
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='⬅️ Попередня',
                callback_data=f'serv_page_{page - 1}'
            ))
        if page < total_pages:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='➡️ Наступна',
                callback_data=f'serv_page_{page + 1}'
            ))
    if len(pagination_buttons)==2:
        pagination_buttons.insert(1,types.InlineKeyboardButton(
                text='Поєднати',
                callback_data='combine'
            ))
    else:
        pagination_buttons.append(types.InlineKeyboardButton(
                text='Поєднати',
                callback_data='combine'
            ))

    if pagination_buttons:
        keyboard.row(*pagination_buttons)

    return keyboard

def send_services_to_combine(services, message, page=1, previous_message=None, chosen_services_ids=None):
    # Видаляємо попереднє повідомлення з майстрами, якщо таке є
    if previous_message != None:
        try:
            bot.delete_message(message.chat.id, previous_message.id)
        except Exception as e:
            print("Error while deleting message:", e)

    keyboard = create_service_keyboard_to_combine(services, page, chosen_services_ids)
    bot.send_message(message.chat.id, 'Виберіть сервіс:', reply_markup=keyboard)

def create_service_keyboard_to_manage(services, page):
    total_services = len(services)
    total_pages = total_services // services_per_page + (1 if total_services % services_per_page > 0 else 0)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    offset = (page - 1) * services_per_page
    current_services = services[offset:offset + services_per_page]

    keyboard = types.InlineKeyboardMarkup()

    for service in current_services:
        keyboard.add(types.InlineKeyboardButton(
            text=service['title'],
            callback_data=f'manage_serv_{service["id_service"]}'
        ))

    # Додаємо кнопки пагінації
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='⬅️ Попередня',
                callback_data=f'serv_page_{page - 1}'
            ))
        if page < total_pages:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='➡️ Наступна',
                callback_data=f'serv_page_{page + 1}'
            ))
    if pagination_buttons:
        keyboard.row(*pagination_buttons)

    return keyboard

def send_services_to_manage(services, message, page=1, previous_message=None):
    # Видаляємо попереднє повідомлення, якщо таке є
    if previous_message != None:
        try:
            bot.delete_message(message.chat.id, previous_message.id)
        except Exception as e:
            print("Error while deleting message:", e)

    keyboard = create_service_keyboard_to_manage(services, page)
    bot.send_message(message.chat.id, 'Виберіть сервіс:', reply_markup=keyboard)


def create_timetable(booked_slots, break_slots, available_slots):
    """
    Створює розклад у форматі словника з вхідних списків.

    :param start_hour: Початкова година робочого дня.
    :param end_hour: Кінцева година робочого дня.
    :param booked_slots: Список заброньованих годин.
    :param break_slots: Список годин перерви.
    :param available_slots: Список доступних годин.
    :return: Розклад у форматі словника.
    """
    timetable = {}
    
    # Створюємо список годин від start_hour до end_hour
    hours_range = range(start_hour, end_hour)
    
    # Додаємо години у форматі "година:00"
    for hour in hours_range:
        time_str = f"{hour:02}:00"
        # Додаємо заброньовані години
        if time_str in booked_slots:
            timetable[time_str] = 'booked'
        # Додаємо години перерви
        elif time_str in break_slots:
            timetable[time_str] = 'break'
        # Додаємо доступні години
        elif time_str in available_slots:
            timetable[time_str] = 'available'
    
    return timetable

from telebot import types

def create_bookings_keyboard(bookings, page = 1, ):
    total_bookings = len(bookings)
    total_pages = total_bookings // bookings_per_page + (1 if total_bookings % bookings_per_page > 0 else 0)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    # Сортуємо список записів за датою та часом
    sorted_bookings = sorted(bookings, key=lambda x: x['date_time'])

    start_index = (page - 1) * bookings_per_page
    end_index = min(start_index + bookings_per_page, total_bookings)
    current_bookings = sorted_bookings[start_index:end_index]

    keyboard = types.InlineKeyboardMarkup()

    for booking in current_bookings:
        date_time = booking['date_time']
        button_text = date_time.strftime("%Y-%m-%d %H:%M")
        keyboard.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f'booking_{booking["id_booking"]}'
        ))

    # Додаємо кнопки пагінації
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='⬅️ Попередня',
                callback_data=f'booking_page_{page - 1}'
            ))
        if page < total_pages:
            pagination_buttons.append(types.InlineKeyboardButton(
                text='➡️ Наступна',
                callback_data=f'booking_page_{page + 1}'
            ))
    if pagination_buttons:
        keyboard.row(*pagination_buttons)

    return keyboard
