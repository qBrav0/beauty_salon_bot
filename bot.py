from xml.dom.expatbuilder import parseString
import telebot
import datetime 
import re

from telebot import types
from telebot import custom_filters
from telebot.storage import StateMemoryStorage
from telebot.callback_data import CallbackData

from models import Admin, Booking, Master, Service, Schedule, Client, Service_has_Master
from config import TOKEN, days_to_create_master_schedule
from utils import (UserStates, send_masters, send_services, send_days, create_working_hours_keyboard, 
                   set_working_hours, create_main_menu_keyboard, send_services_to_combine, 
                   create_service_keyboard_to_combine, create_schedule_keyboard, create_timetable, create_bookings_keyboard,
                   send_services_to_manage)

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

services_factory = CallbackData('service_id', prefix='services')
masters_factory = CallbackData('master_id', prefix='masters')

@bot.message_handler(commands=['start'])
def start(message):  
    bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
    bot.send_message(message.chat.id, f'Вітаю, {message.from_user.first_name}! Я бот салону краси від Ані. Виберіть те, що вас цікавить.')
    bot.send_message(message.chat.id, 'Я з радістю допоможу вам записатись до нас <3', reply_markup=create_main_menu_keyboard(message.chat.id))

@bot.message_handler(state=UserStates.main_menu)
def main_menu(message):
    '''Гловне меню'''
    if message.text == 'Головне меню':  
        bot.send_message(message.chat.id, 'Звісно, що вас цікавить?', reply_markup=create_main_menu_keyboard(message.chat.id))

    elif message.text == 'Коли ви працюєте?': 
        bot.send_message(message.chat.id, 'Ми працюємо\nПн-Пт  з 8:00 до 20:00\nСб-Нд  вихідний')
    
    elif message.text == 'Доступні послуги':
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        back_button = types.KeyboardButton(text='Головне меню')
        keyboard.add(back_button)
        bot.send_message(message.chat.id, 'Секунду, дізнаюсь інформацію...', reply_markup=keyboard)

        send_services(Service.get_services_and_prices(), message)
        bot.add_data(message.from_user.id, message.chat.id, first='serv')

    elif message.text == 'Перегляд майстрів': 
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        back_button = types.KeyboardButton(text='Головне меню')
        keyboard.add(back_button)
        bot.send_message(message.chat.id, 'Секунду, дізнаюсь інформацію...', reply_markup=keyboard)

        send_masters(Master.get_masters(), message) 
        
    elif message.text == 'Мої записи': 
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        reg_button = types.KeyboardButton(text="Поділитись своїм номером телефону", request_contact=True)
        keyboard.add(reg_button)
        bot.send_message(message.chat.id,
                                    "Для цього поділіться, будь-ласка, своїм номером телефону",
                                    reply_markup=keyboard)
        bot.add_data(user_id=message.chat.id, chat_id=message.chat.id, booking=False)

    elif message.text == 'Кнопка влади' and Admin.is_admin(message.chat.id):
        bot.set_state(message.from_user.id, UserStates.admin_menu, message.chat.id)
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)

        if Admin.is_super_admin(message.chat.id):
            add_admin_button = types.KeyboardButton(text="Додати адміністратора")
            keyboard.add(add_admin_button)

        books_schedule_button = types.KeyboardButton(text="Розклад записів")
        masters_button = types.KeyboardButton(text="Керувати майстрами")
        services_button = types.KeyboardButton(text="Керувати послугами")
        keyboard.add(books_schedule_button, masters_button, services_button)
        bot.send_message(message.chat.id,"(Майже) вся влада у твоїх руках", reply_markup=keyboard)

    elif message.text == 'Кнопка Шифу' and Master.is_master(message.chat.id):
        bot.set_state(message.from_user.id, UserStates.master_menu, message.chat.id)
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        my_books_button = types.KeyboardButton(text='Перегляд моїх записів')
        keyboard.add(my_books_button)
        bot.send_message(message.chat.id, "Вітаю в меню майстра", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id,"Вибачте, я не знаю такої команди(")
        bot.send_message(message.chat.id,"Нижче є питання, з якими я можу допомогти. Звертайтесь!")
        
    
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    client_phone = message.contact.phone_number
    client_name = message.contact.first_name
    client_id = Client.create_client(phone_number= client_phone, name= client_name,chat_id=message.chat.id)
    with bot.retrieve_data(message.chat.id) as data:

        if data['booking']:
            booking_date_time = data['date_time']
            service_id = data['service_id']
            master_id = data['master_id']

            Booking.create_booking(client_id, master_id, service_id, booking_date_time)
            Schedule.book_slot(master_id, booking_date_time)

            bot.send_message(message.chat.id, 'Вітаю, ви записались!', reply_markup=create_main_menu_keyboard(message.chat.id))
            bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        elif not data['booking']:
            bookings = Booking.get_bookings_for_client(client_id)
            if bookings:
                msgs = []
                for booking in bookings:
                    master_name = Master.get_master_info_by_id(booking['master_id'])['name']
                    service_name = Service.get_service_info_by_id(booking['service_id'])['title']
                    service_cost = Service.get_service_info_by_id(booking['service_id'])['cost']
                    date = booking['date_time'].strftime('%d.%m.%Y')
                    time = booking['date_time'].strftime('%H:%M')

                    msgs.append(f'Дата: {date}\nЧас на який потрібно підійти: {time}\nІм\'я вашого майстра: '
                                f'{master_name}\nПослуга: {service_name}\nЦіна: {service_cost}грн')

                msg = 'Ось інформація про ваші записи:\n' + '\n\n'.join(msgs)
                bot.send_message(message.chat.id, msg, reply_markup=create_main_menu_keyboard(message.chat.id))
            else:
                bot.send_message(message.chat.id, 'У вас немає записів', reply_markup=create_main_menu_keyboard(message.chat.id))

    bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)

# Обробник натискань на кнопки пагінації майстрів
@bot.callback_query_handler(func=lambda call: call.data.startswith('mast_page_'))
def callback_pagination(call):
    page_number = int(call.data.split('_')[2])
    send_masters(Master.get_masters(), call.message, page=page_number, previous_message=call.message)

# Обробник натискань на кнопки пагінації сервісів
@bot.callback_query_handler(func=lambda call: call.data.startswith('serv_page_'))
def callback_pagination(call):
    page_number = int(call.data.split('_')[2])
    with bot.retrieve_data(call.message.chat.id) as data:
        try:
            master_action = data['master_action']
        except:
            master_action = False
        try:
            master_id = data['master_id']
        except:
            print('Ідентифікатор майстра відсутній')
        try:
            if data['chosen_services_ids'] != None:
                chosen_services_ids = data['chosen_services_ids']
        except:
            if master_action != 'edit':
                chosen_services_ids = []
                services = Service.get_services_by_master_id(master_id)
                for service in services:
                    chosen_services_ids.append(service['id_service'])
                if len(chosen_services_ids) == 0:
                    chosen_services_ids = None

            
    if master_action == 'combine':
        send_services_to_combine(Service.get_services_and_prices(), call.message, page=page_number, previous_message=call.message, chosen_services_ids = chosen_services_ids)
        bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, chosen_services_ids=chosen_services_ids, page=page_number) 
    elif master_action == 'book':
        send_services(Service.get_services_and_prices(), call.message, page=page_number, previous_message=call.message)
    elif master_action == 'edit':
        send_services_to_manage(Service.get_services_and_prices(), call.message, page=page_number, previous_message=call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('manage_serv_'))
def callback_pagination(call):
    service_id = int(call.data.split('_')[2])
    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, service_id=service_id)
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    edit_title_button = types.KeyboardButton(text='Змінити назву')
    edit_cost_button = types.KeyboardButton(text='Змінити ціну')
    keyboard.add(edit_title_button, edit_cost_button)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(chat_id=call.message.chat.id, text='Що саме треба змінити?', reply_markup=keyboard)
    bot.set_state(call.message.chat.id, UserStates.edit_service, call.message.chat.id)

@bot.message_handler(state=UserStates.edit_service_title)
def edit_service_title(message):
    new_service_title = message.text

    with bot.retrieve_data(message.chat.id) as data:
        service_id = data['service_id']
    
    service = Service.get_or_none(Service.id_service == service_id)

    bot.set_state(message.chat.id, UserStates.main_menu, message.chat.id)
    if service:
        service.title = new_service_title
        service.save()
        bot.send_message(message.chat.id, f"Назву послуги змінено на {new_service_title}. Повертаю в головне меню.", reply_markup=create_main_menu_keyboard(message.chat.id))
    else:
        bot.send_message(message.chat.id, "Щось пішло не так. Послуга з вказаним ідентифікатором не знайдена. Повертаю в головне меню", reply_markup=create_main_menu_keyboard(message.chat.id))


@bot.message_handler(state=UserStates.edit_service_cost)
def edit_service_cost(message):
    new_service_cost = int(message.text)

    with bot.retrieve_data(message.chat.id) as data:
        service_id = data['service_id']

    service = Service.get_or_none(Service.id_service == service_id)

    bot.set_state(message.chat.id, UserStates.main_menu, message.chat.id)
    if service:

        service.cost = new_service_cost
        service.save()
        bot.send_message(message.chat.id, f"Вартість послуги змінено на {new_service_cost}. Повертаю в головне меню.", reply_markup=create_main_menu_keyboard(message.chat.id))
    else:
        bot.send_message(message.chat.id, "Щось пішло не так. Послуга з вказаним ідентифікатором не знайдена. Повертаю в головне меню.", reply_markup=create_main_menu_keyboard(message.chat.id))

@bot.message_handler(state=UserStates.edit_service)
def edit_service(message):
    if message.text == 'Змінити назву':
        bot.send_message(message.chat.id, text="Нову назву послуги")
        bot.set_state(message.chat.id, UserStates.edit_service_title, message.chat.id)
    
    elif message.text == 'Змінити ціну':
        bot.send_message(message.chat.id, text="Нову ціну послуги")
        bot.set_state(message.chat.id, UserStates.edit_service_cost, message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('combine_serv_'))
def callback_pagination(call):
    with bot.retrieve_data(call.message.chat.id) as data:
        master_id = data['master_id']
        try:
            if data['chosen_services_ids'] != None:
                chosen_services_ids = data['chosen_services_ids']
        except:
            chosen_services_ids = []
            services = Service.get_services_by_master_id(master_id)
            for service in services:
                chosen_services_ids.append(service['id_service'])

            if len(chosen_services_ids) == 0:
                chosen_services_ids = []
    
        try:
            page=data['page']
        except:
            page = 1

    if int(call.data.split('_')[2]) in chosen_services_ids:
        chosen_services_ids.remove(int(call.data.split('_')[2]))
    else:
        chosen_services_ids.append(int(call.data.split('_')[2]))

    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, chosen_services_ids=chosen_services_ids)
    keyboard = create_service_keyboard_to_combine(Service.get_services_and_prices(), page, chosen_services_ids)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('combine'))
def callback_combine(call):
    with bot.retrieve_data(call.message.chat.id) as data:
        chosen_services_ids = data['chosen_services_ids']
        master_id = data['master_id']
    
    connected_services_ids = []
    for service in Service.get_services_by_master_id(master_id):
        connected_services_ids.append(service['id_service'])

    print(connected_services_ids, chosen_services_ids)
    for service_id in chosen_services_ids:
        if service_id not in connected_services_ids:
            Service_has_Master.connect_service_to_master(service_id,master_id)
            
    for connected_service_id in connected_services_ids:
        if connected_service_id not in chosen_services_ids:
            Service_has_Master.disconnect_service_from_master(connected_service_id, master_id)


    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, master_action = 'book', chosen_services_ids = chosen_services_ids)
    bot.set_state(call.message.chat.id, UserStates.main_menu, call.message.chat.id)
    bot.send_message(call.message.chat.id, text='До майстра успішно додані нові послуги. Повертаю до головного меню', reply_markup=create_main_menu_keyboard(call.message.chat.id))

    

# Обробник натискань на кнопки пагінації днів
@bot.callback_query_handler(func=lambda call: call.data.startswith('day_page_'))
def callback_pagination(call):
    page_number = int(call.data.split('_')[2])
    with bot.retrieve_data(call.message.chat.id) as data:
        master_id = data['master_id']
        try:
            change_schedule = data['change_schedule']
        except:
            change_schedule = False

    if not change_schedule:
        send_days(Schedule.get_available_days_with_schedule(master_id), call.message, page=page_number, previous_message=call.message)
    else:
        send_days(Schedule.get_days_with_schedule(master_id), call.message, page=page_number, previous_message=call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('serv_'))
def services_callback(call: types.CallbackQuery):
    service_id = int(call.data[5:])
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton(text='Головне меню')
    keyboard.add(back_button)
    masters = Master.get_masters_with_service_ids(service_id)
    if len(masters) > 0:
        bot.send_message(call.message.chat.id, 'Ось майстри, які надають цю послугу', reply_markup=keyboard)
        send_masters(masters, call.message, service_id, previous_message=call.message, book=True)
    else:
        bot.send_message(call.message.chat.id, 'Нажаль немає майстрів, які роблять цю послугу')


@bot.callback_query_handler(func=lambda call: call.data.startswith('mast_'))
def masters_callback(call: types.CallbackQuery):
    master_id = int(call.data[5:])
    with bot.retrieve_data(call.message.chat.id) as data:
        try:
            chosen_services_ids = data['chosen_services_ids']
            print(chosen_services_ids)
        except:
            chosen_services_ids = []
            services = Service.get_services_by_master_id(master_id)
            for service in services:
                chosen_services_ids.append(service['id_service'])
            if len(chosen_services_ids) == 0:
                chosen_services_ids = None
            print(chosen_services_ids)
        try:
            master_action = data['master_action']
        except:
            master_action = 'book'

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    back_button = types.KeyboardButton(text='Головне меню')
    keyboard.add(back_button)
    if master_action == 'book':
        services = Service.get_services_by_master_id(master_id)
        if len(services) > 0:
            bot.send_message(call.message.chat.id, 'Ось послуги, які надає цей майстер', reply_markup=keyboard)
            send_services(services, call.message, master_id, previous_message=call.message, book=True)
        else:
            bot.send_message(call.message.chat.id, 'Нажаль цей майстер не надає ніяких послуг')

    elif master_action == 'combine':
        bot.send_message(call.message.chat.id, 'Виберіть послуги які цей майстер буде мати', reply_markup=keyboard)
        send_services_to_combine(Service.get_services_and_prices(), call.message, chosen_services_ids=chosen_services_ids)
        bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, master_id= master_id)
        
    elif master_action == 'change_schedule':
        bot.send_message(call.message.chat.id, 'Виберіть день, на який змінити розклад')
        bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, master_id= master_id, change_schedule = True)
        send_days(Schedule.get_days_with_schedule(master_id), call.message, previous_message=call.message, change_schedule = True)
        

@bot.callback_query_handler(func=lambda call: call.data.startswith('book_'))
def book_callback(call: types.CallbackQuery):

    master_id = int(call.data.split('_')[1])
    service_id = int(call.data.split('_')[2])
    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, master_id=master_id, service_id=service_id)
    schedule = Schedule.get_available_days_with_schedule(master_id)
    send_days(schedule, call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('change_schedule_day_'))
def change_schedule_day_callback(call: types.CallbackQuery):  
    day = call.data.split('_')[3]
    with bot.retrieve_data(call.message.chat.id) as data:
        master_id = data['master_id']

    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, change_master_schedule_day=day)
    booked_slots, break_slots, available_slots = Schedule.get_all_slots(master_id,day)
    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, booked_slots = booked_slots, break_slots = break_slots, available_slots = available_slots)
    bot.delete_message(call.message.chat.id, call.message.id)
    bot.send_message(call.message.chat.id, 'Внесіть необхідні зміни', reply_markup=create_schedule_keyboard(booked_slots, break_slots, available_slots))
    

@bot.callback_query_handler(func=lambda call: call.data.startswith('bookday_'))
def bookday_callback(call: types.CallbackQuery):  
    day = call.data.split('_')[1]
    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, day=day)
    with bot.retrieve_data(call.message.chat.id) as data:
        master_id = data['master_id']

    available_hours = Schedule.get_available_slots(master_id, day)

    keyboard = types.InlineKeyboardMarkup(row_width=4)
    for hour in available_hours:
        btn = types.InlineKeyboardButton(
            text=hour,
            callback_data='bookhour_' + hour)
        keyboard.add(btn)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Ось вільні години в цей день', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('bookhour_'))
def bookhour_callback(call: types.CallbackQuery):  
    hour = call.data.split('_')[1]
    with bot.retrieve_data(call.message.chat.id) as data:
        day = data['day']

    # Перетворюємо рядки з годиною і днем у об'єкт типу datetime.time
    hour = datetime.datetime.strptime(hour, '%H:%M').time()
    day = datetime.datetime.strptime(day, '%Y-%m-%d').date()
    full_date_time = datetime.datetime.combine(day, hour)

    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, date_time=full_date_time)

    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    share_contact_button = types.KeyboardButton(text="Поділитись своїм номером телефону", request_contact=True)
    keyboard.add(share_contact_button)

    bot.send_message(call.message.chat.id,
                                    "Для бронювання поділіться, будь-ласка, своїм номером телефону",
                                    reply_markup=keyboard)
    
    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, booking=True)


@bot.message_handler(state=UserStates.admin_menu)
def admin_menu(message):
    '''Меню адміністратора'''

    if message.text == 'Головне меню':
        bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        bot.send_message(message.chat.id, 'Добре, повертаю в голвне меню', reply_markup=create_main_menu_keyboard(message.chat.id))
        
    elif message.text == "Додати адміністратора" and Admin.is_super_admin(message.chat.id):
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        back_button = types.KeyboardButton(text='Головне меню')
        keyboard.add(back_button)
        bot.send_message(message.chat.id, text="Введіть номер телефону(через +380) аккаунту якому треба видати адмінські права.", reply_markup=keyboard)
        bot.send_message(message.chat.id, text='ВАЖЛИВО! Цей аккаунт вже мав ділитись своїм номером телефону(своїм контактом). Наприклад через кнопку "Мої записи"')
        bot.set_state(message.from_user.id, UserStates.add_new_admin, message.chat.id)

    elif message.text == "Керувати майстрами":  
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        add_master_button = types.KeyboardButton(text="Додати нового")
        edit_master_button = types.KeyboardButton(text="Редагувати існуючого")
        keyboard.add(add_master_button, edit_master_button)
        bot.send_message(message.chat.id, text='Що саме треба зробити з майстрами?', reply_markup=keyboard)
        bot.set_state(message.from_user.id, UserStates.manage_master_menu, message.chat.id)

    elif message.text == "Розклад записів":  
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        main_menu_button = types.KeyboardButton(text="Головне меню")
        keyboard.add(main_menu_button)
        bot.send_message(message.chat.id, text="Секнду, дізнаюсь інформацію...", reply_markup=keyboard)

        bot.add_data(message.from_user.id, message.chat.id, role_for_schedule = 'admin')
        inline_keyboard = create_bookings_keyboard(Booking.get_all_bookings())
        bot.send_message(message.chat.id, text="Ось список бронювань", reply_markup=inline_keyboard)
        
    elif message.text == "Керувати послугами":  
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        add_service_button = types.KeyboardButton(text="Додати нову послугу")
        edit_service_button = types.KeyboardButton(text="Редагувати існуючу")
        keyboard.add(add_service_button, edit_service_button)
        bot.send_message(message.chat.id, text='Що саме треба зробити з послугами?', reply_markup=keyboard)
        bot.set_state(message.from_user.id, UserStates.manage_service, message.chat.id)
        

@bot.message_handler(state=UserStates.master_menu)
def master_menu(message):
    '''Меню майстрів'''
    master = Master.get_or_none(Master.chat_id == message.chat.id)
    if message.text == 'Перегляд моїх записів':
        reply_keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        main_menu_button = types.KeyboardButton(text="Головне меню")
        reply_keyboard.add(main_menu_button)
        bot.send_message(message.chat.id, text='Секунуду, шукаю ваші записи...', reply_markup=reply_keyboard)
        if master:
            master_bookings = Booking.get_master_bookings(master.id_master)
            if len(master_bookings) > 0:
                # Виведення записів майстра
                inline_keyboard = create_bookings_keyboard(master_bookings)
                bot.add_data(message.from_user.id, message.chat.id, role_for_schedule = 'master', id_master = master.id_master)
                bot.send_message(message.chat.id, text='Ось ваші записи:', reply_markup=inline_keyboard)
            else:
                bot.send_message(message.chat.id, "У вас немає записів на даний момент.")
        else:
            bot.send_message(message.chat.id, "Ви не зареєстровані в системі як майстер.")
    elif message.text == 'Головне меню':
        bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        bot.send_message(message.chat.id, 'Добре, повертаю в голвне меню', reply_markup=create_main_menu_keyboard(message.chat.id))
        

@bot.message_handler(state=UserStates.manage_service)
def manage_service(message):
    '''Меню роботи з сервісами'''

    if message.text == "Додати нову послугу":
        bot.send_message(message.chat.id, text='Введіть назву послуги.')
        bot.set_state(message.from_user.id, UserStates.add_service, message.chat.id)
        bot.add_data(message.from_user.id, message.chat.id, stage = 2.1)

    elif message.text == "Редагувати існуючу":
        bot.add_data(message.from_user.id, message.chat.id, master_action = 'edit')
        send_services_to_manage(Service.get_services_and_prices(), message)
        bot.set_state(message.from_user.id, UserStates.manage_service, message.chat.id)

@bot.message_handler(state=UserStates.add_service)
def add_new_service(message):
    '''Додатинову послугу'''
    new_service_info = message.text
    with bot.retrieve_data(message.chat.id) as data:
        stage = data['stage']
        try:
            title = data['title']
        except:
            pass
    
    if stage == 2.1:
        bot.add_data(message.from_user.id, message.chat.id, title = new_service_info, stage = 2.2)
        bot.send_message(message.chat.id, text='Введіть ціну за цю послугу.')
    elif stage == 2.2:
        Service.create_service(title, new_service_info)
        bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        bot.send_message(message.chat.id, text='Нову послугу упішно додано. Повертаю в головне меню', reply_markup=create_main_menu_keyboard(message.chat.id))

@bot.message_handler(state=UserStates.manage_master_menu)
def manage_master_menu(message):
    '''Меню роботи з майстрами'''

    if message.text == "Додати нового":
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        main_menu_button = types.KeyboardButton(text="Головне меню")
        keyboard.add(main_menu_button)
        bot.set_state(message.from_user.id, UserStates.add_master, message.chat.id)
        bot.send_message(message.chat.id, text="Введіть номер телефону(через +380) аккаунту який буде майстром.", reply_markup=keyboard)
        bot.send_message(message.chat.id, text='ВАЖЛИВО! Цей аккаунт вже мав ділитись своїм номером телефону(своїм контактом). Наприклад через кнопку "Мої записи"')
    elif message.text == "Редагувати існуючого":
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        add_master_button = types.KeyboardButton(text="Додати майстру послугу")
        masters_schedule_button = types.KeyboardButton(text="Розклад майстра")
        keyboard.add(add_master_button, masters_schedule_button)
        bot.send_message(message.chat.id, text='Що саме треба змінити?', reply_markup=keyboard)
        bot.set_state(message.from_user.id, UserStates.edit_master, message.chat.id)
    

@bot.message_handler(state=UserStates.edit_master)
def edit_master(message):
    '''Редагування майстра'''

    if message.text == 'Головне меню':
        bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        bot.send_message(message.chat.id, 'Добре, повертаю в голвне меню', reply_markup=create_main_menu_keyboard(message.chat.id))
    
    elif message.text == 'Додати майстру послугу':   
        reply_keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        main_menu_button = types.KeyboardButton(text="Головне меню")
        reply_keyboard.add(main_menu_button)
        bot.send_message(message.chat.id, text='Секунуду, шукаю ваші записи...', reply_markup=reply_keyboard)  
        send_masters(Master.get_masters(), message)
        bot.add_data(message.from_user.id, message.chat.id, master_action = 'combine')

    elif message.text == "Розклад майстра":  
        reply_keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        main_menu_button = types.KeyboardButton(text="Головне меню")
        reply_keyboard.add(main_menu_button)
        bot.send_message(message.chat.id, text='Секунуду, шукаю ваші записи...', reply_markup=reply_keyboard)
        send_masters(Master.get_masters(), message)
        bot.add_data(message.from_user.id, message.chat.id, master_action = 'change_schedule')

        

@bot.message_handler(state=UserStates.add_master)
def add_master(message):
    '''Додавання нового майстра'''
    new_master_as_client = Client.get_client_info_by_phone_number(message.text)
    if message.text == 'Головне меню':
        bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        bot.send_message(message.chat.id, 'Добре, повертаю в голвне меню', reply_markup=create_main_menu_keyboard(message.chat.id))
        
    elif new_master_as_client:
        bot.send_message(message.chat.id, text='Тепер напишіть спеціалізацію нового майстра')
        bot.add_data(message.from_user.id, message.chat.id, new_master_as_client=new_master_as_client, stage = 2.1)
        bot.set_state(message.from_user.id, UserStates.add_master_2, message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Перепрошую, данного номеру телефону в моїй базі немає. Перевірте правильність номеру або переконайтесь що адмін відправив свій контакт до бота(наприклад через кнопку "Мої записи")')


@bot.message_handler(state=UserStates.add_master_2)
def add_master_stage_2(message):
    '''Додавання нового майстра стадія 2'''
    with bot.retrieve_data(message.chat.id) as data:
        stage = data['stage']
    new_master_info = message.text
    if stage == 2.1:
        bot.add_data(message.from_user.id, message.chat.id, specialty=new_master_info, stage=2.2)
        bot.send_message(message.chat.id, text='Тепер напишіть досвід нового майстра')

    elif stage == 2.2:
        # Перевірка на правильний формат досвіду (ціле число або дробове число)
        if re.match(r'^\d+(\.\d+)?$', new_master_info):
            bot.add_data(message.from_user.id, message.chat.id, experience=new_master_info, stage=2.3)
            bot.send_message(message.chat.id, text='Тепер напишіть інстаграм нового майстра')
        else:
            bot.send_message(message.chat.id, text='Невірний формат досвіду. Будь ласка, введіть ціле або дробове число.')

    elif stage == 2.3:
        bot.add_data(message.from_user.id, message.chat.id, instagram=new_master_info)
        bot.send_message(message.chat.id, text='Тепер напишіть дату початку роботи нового майстра')
        bot.send_message(message.chat.id, text='ВАЖЛИВО! Дата початку роботи у форматі РРРР-ММ-ДД')
        bot.set_state(message.from_user.id, UserStates.add_master_3, message.chat.id)


@bot.message_handler(state=UserStates.add_master_3)
def add_master_stage_3(message):
    '''Додавання нового майстра стадія 3'''
    start_work_day = message.text

    # Перевірка на правильний формат дати (РРРР-ММ-ДД)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', start_work_day):
        with bot.retrieve_data(message.chat.id) as data:
            new_master_as_client = data['new_master_as_client']
            specialty = data['specialty']
            experience = data['experience']
            instagram = data['instagram']
        
        new_master_info = (new_master_as_client['name'],specialty, experience, instagram, new_master_as_client['chat_id'], start_work_day)
        bot.add_data(message.from_user.id, message.chat.id, new_master_info=new_master_info)
        bot.send_message(message.chat.id, text='Оберіть години роботи майстра. Години які не будуть помічені ✅, автоматично будуть неробочими', reply_markup=create_working_hours_keyboard())
        
        # Якщо дата введена у правильному форматі, продовжуємо обробку
    else:
        bot.send_message(message.chat.id, text='Невірний формат дати. Будь ласка, введіть дату у форматі РРРР-ММ-ДД.')




@bot.callback_query_handler(func=lambda call: call.data.startswith('change_schedule'))
def change_schedulecallback(call):
    with bot.retrieve_data(call.message.chat.id) as data:
        booked_slots = data['booked_slots']
        break_slots = data['break_slots']
        available_slots = data['available_slots']
        master_id = data['master_id']
        day = data['change_master_schedule_day']

    new_timetable = create_timetable(booked_slots, break_slots, available_slots)
    schedule = Schedule.get_or_none((Schedule.master_id == master_id) & (Schedule.date == day))
    bot.set_state(call.from_user.id, UserStates.main_menu, call.message.chat.id)        
    if schedule:
        # Оновлюємо розклад
        updated = schedule.update_schedule_for_date(new_timetable)
        if updated:
            bot.send_message(call.message.chat.id, text='Вітаю, розклад оновлено. Повертаю до головного меню.', reply_markup=create_main_menu_keyboard(call.message.chat.id))
        else:
            bot.send_message(call.message.chat.id, text='Щось пішло не так, розклад на цей день відсутній😞. Повертаю до головного меню.', reply_markup=create_main_menu_keyboard(call.message.chat.id))
    else:
        bot.send_message(call.message.chat.id, text='Щось пішло не так, розклад на цей день відсутній😞. Повертаю до головного меню.', reply_markup=create_main_menu_keyboard(call.message.chat.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('change_hour_'))
def change_hour_callback(call):
    hour = str(call.data.split('_')[2]).zfill(2) + ":00"

    with bot.retrieve_data(call.message.chat.id) as data:
        booked_slots = data['booked_slots']
        break_slots = data['break_slots']
        available_slots = data['available_slots']

    if hour in break_slots:
        break_slots.remove(hour)
        available_slots.append(hour)
    elif hour in available_slots:
        available_slots.remove(hour)
        break_slots.append(hour)
    elif hour in booked_slots:
        bot.answer_callback_query(callback_query_id=call.id, text="Ця година заброньована. Ви не можете її змінити. Якщо ви хочите її змінити, спочатку відмініть бронювання")

    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, booked_slots = booked_slots, break_slots = break_slots, available_slots = available_slots)
    keyboard = create_schedule_keyboard(booked_slots, break_slots, available_slots)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('hour_'))
def callback_choose_hour(call):
    chosen_hours = []
    with bot.retrieve_data(call.message.chat.id) as data:
        try:
            if data['chosen_hours'] != None:
                chosen_hours = data['chosen_hours']
        except:
            print("Скоріш за все не було обрано жодної робочою години. Не роби так...(доведеться почати зі /start)")

    if int(call.data.split('_')[1]) in chosen_hours:
        chosen_hours.remove(int(call.data.split('_')[1]))
    else:
        chosen_hours.append(int(call.data.split('_')[1]))

    bot.add_data(user_id=call.message.chat.id, chat_id=call.message.chat.id, chosen_hours=chosen_hours)
    keyboard = create_working_hours_keyboard(chosen_hours)
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'add_master')
def callback_done(call):
    with bot.retrieve_data(call.message.chat.id) as data:
        chosen_hours = data['chosen_hours']
        new_master_info = data['new_master_info']
    
    working_hours_dict = set_working_hours(chosen_hours)
    # Створення майстра
    new_master = Master.create_master(new_master_info[0], new_master_info[1], new_master_info[2], new_master_info[3], new_master_info[4])
    new_master.set_working_hours(working_hours_dict)
    new_master.save()

    start_date = datetime.datetime.strptime(new_master_info[5], '%Y-%m-%d').date()
    # Цикл для створення розкладу на вказану кількість днів
    for day in range(days_to_create_master_schedule):
        # Отримуємо поточну дату
        current_date = start_date + datetime.timedelta(days=day)

        # Визначаємо, чи є поточний день робочим або вихідним
        if day % 3 < 2:  # Перші два дні робочі, потім один вихідний
            # Якщо день робочий, додаємо робочі години з new_master.working_hours
            Schedule.create_schedule_for_working_day(new_master.id_master, current_date)
        else:
            Schedule.create_schedule_for_weekend(new_master.id_master, current_date)
    bot.send_message(chat_id=call.message.chat.id, text='Майтра успішно додано, повертаю в головне меню', reply_markup=create_main_menu_keyboard(call.message.chat.id))
    bot.set_state(call.from_user.id, UserStates.main_menu, call.message.chat.id)


@bot.message_handler(state=UserStates.add_new_admin)
def add_new_admin(message):
    '''Додавання нового адміна'''
    client = Client.get_client_info_by_phone_number(message.text)
    if message.text == 'Головне меню':
        bot.set_state(message.from_user.id, UserStates.main_menu, message.chat.id)
        bot.send_message(message.chat.id, 'Добре, повертаю в голвне меню', reply_markup=create_main_menu_keyboard(message.chat.id))
        
    elif client:
        bot.add_data(message.from_user.id, message.chat.id, client=client)
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        add_admin_button = types.InlineKeyboardButton(text="Так", callback_data='add_admin')
        not_admin_button = types.InlineKeyboardButton(text="Ні", callback_data='not_admin')
        keyboard.add(add_admin_button, not_admin_button)
        bot.send_message(message.chat.id, f'Ви впевнені, що хочете додати {client["name"]} з номером телефона {client["phone_number"]} в адміністратори?',reply_markup=keyboard)
    elif not client:
        bot.send_message(message.chat.id, 'Перепрошую, данного номеру телефону в моїй базі немає. Перевірте правильність номеру або переконайтесь що адмін відправив свій контакт до бота(наприклад через кнопку "Мої записи")')


@bot.callback_query_handler(func=lambda call: call.data.startswith('add_admin'))
def add_admin(call: types.CallbackQuery):  
    with bot.retrieve_data(call.message.chat.id) as data:
        Admin.create_admin(name=data['client']['name'], phone_number=data['client']['phone_number'],chat_id=data['client']['chat_id'])  
    bot.set_state(call.from_user.id, UserStates.main_menu, call.message.chat.id)

    bot.send_message(call.message.chat.id, 'Вітаю, Ви успішно додали нового адміністратора! Повертаю в головне меню', reply_markup=create_main_menu_keyboard(call.message.chat.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('not_admin'))
def bookhour_callback(call: types.CallbackQuery):  
    bot.set_state(call.from_user.id, UserStates.main_menu, call.message.chat.id)

    bot.send_message(call.message.chat.id, 'Певно він не достоїн звання Воїну дракона XD\nПовертаю в головне меню ', reply_markup=create_main_menu_keyboard(call.message.chat.id))


# Обробник для кнопок пагінації
@bot.callback_query_handler(func=lambda call: call.data.startswith('booking_page_'))
def handle_booking_pagination(call):
    # Отримуємо номер сторінки з callback_data
    page = int(call.data.split('_')[-1])

    # Отримуємо список всіх записів
    all_bookings = Booking.get_all_bookings()

    # Створюємо нову клавіатуру для поточної сторінки
    keyboard = create_bookings_keyboard(all_bookings, page)

    # Оновлюємо повідомлення з клавіатурою пагінації
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

# Обробник для кнопок бронювань
@bot.callback_query_handler(func=lambda call: call.data.startswith('booking_'))
def handle_booking_button(call):
    with bot.retrieve_data(call.message.chat.id) as data:
        role_for_schedule = data['role_for_schedule']
    # Отримуємо ID бронювання з callback_data
    booking_id = int(call.data.split('_')[-1])

    # Отримуємо інформацію про обране бронювання
    booking_info = Booking.get_by_id(booking_id)

    # Отримуємо ім'я та номер телефона клієнта
    client_name = booking_info.client_id.name
    client_phone = booking_info.client_id.phone_number

    # Отримуємо інформацію про майстра
    master_name = booking_info.master_id.name

    # Отримуємо дату та час бронювання
    booking_datetime = booking_info.date_time.strftime("%Y-%m-%d %H:%M")

    # Формуємо повідомлення з повною інформацією про бронювання
    message_text = (
        f"Ім'я клієнта: {client_name}\n"
        f"Номер телефона клієнта: {client_phone}\n"
        f"Майстер: {master_name}\n"
        f"Час бронювання: {booking_datetime}\n"
        "\n"
        "Оберіть дію:"
    )

    # Створюємо інлайн клавіатуру з кнопками "Назад" і "Скасувати бронювання"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data="back_to_bookings"))
    if role_for_schedule == 'admin':
        keyboard.add(types.InlineKeyboardButton(text="Скасувати бронювання", callback_data=f"cancel_booking_{booking_id}"))

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message_text, reply_markup=keyboard)


# Обробник для кнопки "Скасувати бронювання"
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_booking_'))
def handle_cancel_booking(call):
    # Отримуємо ID бронювання з callback_data
    booking_id = int(call.data.split('_')[-1])

    # Отримуємо інформацію про обране бронювання
    booking_info = Booking.get_by_id(booking_id)

    #Відміняємо бронювапння в розкладі
    Schedule.cancel_booking(booking_info.master_id, booking_info.date_time)
    
    # Видаляємо бронювання
    booking_info.delete_instance()


    # Відправляємо повідомлення про успішне скасування бронювання
    bot.answer_callback_query(callback_query_id=call.id, text="Бронювання скасовано")
    bot.send_message(call.message.chat.id, 'Бронювання скасовано. Повертаю в головне меню. ', reply_markup=create_main_menu_keyboard(call.message.chat.id))

# Обробник для кнопки "Назад" у списку бронювань
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_bookings')
def handle_back_to_bookings(call):
    with bot.retrieve_data(call.message.chat.id) as data:
        role_for_schedule = data['role_for_schedule']
        try:
            id_master = data['id_master']
        except:
            pass
    # Отримуємо всі бронювання
    if role_for_schedule == 'admin':
        bookings = Booking.get_all_bookings()
    elif role_for_schedule == 'master':
        bookings = Booking.get_master_bookings(id_master)

    # Формуємо повідомлення зі списком всіх бронювань
    message_text = "Список всіх бронювань:"

    # Відправляємо повідомлення зі списком бронювань та кнопками
    keyboard = create_bookings_keyboard(bookings)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message_text, reply_markup=keyboard)



bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling()
