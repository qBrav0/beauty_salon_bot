import datetime
import json
import peewee as pw

from config import start_hour, end_hour

db = pw.SqliteDatabase('krasunya.db')

class BaseModel(pw.Model):
    class Meta:
        database = db

class Admin(BaseModel):
    """Адміністратор"""

    id_admin = pw.AutoField()
    name = pw.TextField(null=False)
    phone_number = pw.TextField(null=False)
    super_admin = pw.BooleanField(default=False)
    chat_id = pw.IntegerField(unique=True, null=False)

    @classmethod
    def create_admin(cls, name, phone_number, chat_id):
        """
        Створює нового адміністратора без суперправ.

        :param name: Ім'я адміністратора.
        :param phone_number: Номер телефону адміністратора.
        :param chat_id: Чат ID адміністратора.
        :return: Створений об'єкт адміністратора.
        """
        return cls.create(
            name=name,
            phone_number=phone_number,
            chat_id=chat_id
        )
    
    @classmethod
    def is_super_admin(cls, chat_id):
        """
        Перевіряє, чи є адміністратор з заданим чат ID суперадміном.

        :param chat_id: Чат ID для перевірки.
        :return: True, якщо адміністратор з таким чат ID є суперадміном, інакше - False.
        """
        admin = cls.get_or_none(cls.chat_id == chat_id)
        if admin:
            return admin.super_admin
        return False

    @classmethod
    def is_admin(cls, chat_id):
        """
        Перевіряє, чи є заданий chat_id в списку адміністраторів.

        :param chat_id: Чат ID для перевірки.
        :return: True, якщо адміністратор з таким chat_id існує, інакше - False.
        """
        return cls.select().where(cls.chat_id == chat_id).exists()
    
    class Meta:
        db_table = 'admins'

class Master(BaseModel):
    """Майстер"""

    id_master = pw.AutoField()
    name = pw.TextField(null=False)
    specialty = pw.TextField(null=False)
    experience = pw.FloatField(null=False)
    instagram = pw.TextField(null=False)
    working_hours = pw.CharField(max_length=500, default='{}', null=False)  # JSON-поле для збереження розкладу
    chat_id = pw.IntegerField(unique=True, null=False)

    def set_working_hours(self, working_hours):
        """
        Встановлює розклад роботи у форматі JSON.

        :param timetable: Розклад роботи у форматі словника, який буде перетворено в JSON.
        """

        self.working_hours = json.dumps(working_hours)
        

    @staticmethod
    def get_working_hours_by_id(master_id):
        """
        Повертає розклад роботи майстра за його ідентифікатором.

        :param master_id: Ідентифікатор майстра.
        :return: Розклад роботи майстра у форматі словника, або None, якщо майстра з вказаним ідентифікатором не знайдено.
        """
        master = Master.get_or_none(id_master=master_id)
        if master:
            return json.loads(master.working_hours)
        else:
            return None
    @classmethod
    def create_master(cls, name, specialty, experience, instagram, chat_id):
        """
        Створює нового майстра.

        :param name: Ім'я майстра.
        :param specialty: Спеціалізація майстра.
        :param experience: Досвід роботи майстра.
        :param instagram: Профіль майстра в Instagram.
        :param chat_id: chat_id майстра.
        :return: Створений майстер.
        """
        new_master = cls.create(
            name=name,
            specialty=specialty,
            experience=experience,
            instagram=instagram,
            chat_id = chat_id
        )
        return new_master

    @classmethod
    def is_master(cls, chat_id):
        """
        Перевіряє, чи є майстер з заданим чат ID.

        :param chat_id: Чат ID для перевірки.
        :return: True, якщо майстер з таким чат ID існує, інакше - False.
        """
        return cls.select().where(cls.chat_id == chat_id).exists()

    @classmethod
    def get_masters(cls):
        """
        Повертає список майстрів разом з усією їхньою інформацією.

        :return: Список майстрів та їхні дані.
        """
        masters_info = []
        for master in cls.select():
            masters_info.append({
                'id_master': master.id_master,
                'name': master.name,
                'specialty': master.specialty,
                'experience': master.experience,
                'instagram': master.instagram
            })
        return masters_info
    
    @classmethod
    def get_master_info_by_id(cls, master_id):
        """
        Повертає інформацію про майстра за його ідентифікатором.

        :param master_id: ID майстра.
        :return: Інформація про майстра.
        """
        master_info = cls.get_or_none(cls.id_master == master_id)
        if master_info:
            return {
                'id_master': master_info.id_master,
                'name': master_info.name,
                'specialty': master_info.specialty,
                'experience': master_info.experience,
                'instagram': master_info.instagram
            }
        else:
            return None
        
    @classmethod
    def get_masters_with_service_ids(cls, service_id):
        """
        Повертає всі послуги вказаного майстра.

        :param master_id: ID майстра.
        :return: Список послуг, які надає вказаний майстер.
        """
        services_by_master = []
        for master in cls.select().join(Service_has_Master).where(Service_has_Master.service_id == service_id).distinct():
            services_by_master.append({
                'id_master': master.id_master,
                'name': master.name,
                'specialty': master.specialty,
                'experience': master.experience,
                'instagram': master.instagram
            })
        return services_by_master

    class Meta:
        order_by = 'id_master'
        db_table = 'masters'



class Service(BaseModel):
    """Послуга"""

    id_service = pw.AutoField()
    title = pw.TextField(null=False)
    cost = pw.IntegerField(null=False)

    @classmethod
    def create_service(cls, title, cost):
        """
        Створює нову послугу.

        :param title: Назва послуги.
        :param cost: Вартість послуги.
        :return: Створена послуга.
        """
        new_service = cls.create(
            title=title,
            cost=cost
        )
        return new_service

    @classmethod
    def get_services_and_prices(cls):
        """
        Повертає словник з послугами та їх цінами.

        :return: Словник, де ключ - назва послуги, значення - ціна послуги.
        """
        services = []
        for service in cls.select():
            services.append({
                'id_service': service.id_service,
                'title': service.title,
                'cost': service.cost
            })
        return services
        

    @classmethod
    def get_services_by_master_id(cls, master_id):
        """
        Повертає всі послуги вказаного майстра.

        :param master_id: ID майстра.
        :return: Список послуг, які надає вказаний майстер.
        """
        services_by_master = []
        for service in cls.select().join(Service_has_Master).where(Service_has_Master.master_id == master_id):
            services_by_master.append({
                'id_service': service.id_service,
                'title': service.title,
                'cost': service.cost
            })
        return services_by_master
    
    
    @classmethod
    def get_service_info_by_id(cls, service_id):
        """
        Повертає інформацію про послугу за її ідентифікатором.

        :param service_id: ID послуги.
        :return: Інформація про послугу.
        """
        service_info = cls.get_or_none(cls.id_service == service_id)
        if service_info:
            return {
                'id_service': service_info.id_service,
                'title': service_info.title,
                'cost': service_info.cost
            }
        else:
            return None
        

    class Meta:
        order_by = 'id_service'
        db_table = 'services'


class Service_has_Master(BaseModel):
    """Зв'язок багато до багатьох між Service та Master"""

    service_id = pw.ForeignKeyField(Service)
    master_id = pw.ForeignKeyField(Master)

    @classmethod
    def connect_service_to_master(cls, service_id, master_id):
        """
        Поєднує послугу з майстром.

        :param service_id: ID послуги.
        :param master_id: ID майстра.
        :return: Зв'язок між послугою та майстром.
        """
        connection = cls.create(
            service_id=service_id,
            master_id=master_id
        )
        return connection
    
    @classmethod
    def disconnect_service_from_master(cls, service_id, master_id):
        """
        Від'єднує послугу від майстра.

        :param service_id: ID послуги.
        :param master_id: ID майстра.
        :return: Кількість видалених зв'язків.
        """
        query = cls.delete().where((cls.service_id == service_id) & (cls.master_id == master_id))
        return query.execute()
    
    class Meta:
        db_table = 'services_have_masters'


class Client(BaseModel):
    """Клієнт"""

    id_client = pw.AutoField()
    phone_number = pw.TextField(null=False)
    name = pw.TextField(null=False)
    chat_id = pw.IntegerField(unique=True, null=False)

    @classmethod
    def get_client_info_by_phone_number(cls, phone_number):
        """
        Повертає інформацію про клієнта за його номером телефону.

        :param phone_number: Номер телефону клієнта.
        :return: Інформація про клієнта у форматі словника або None, якщо клієнт з таким номером телефону не знайдений.
        """
        # Видаляємо символ "+" перед номером телефону, якщо він є
        phone_number = phone_number.lstrip('+')

        # Шукаємо клієнта якщо номер телефону без "+"
        client = cls.get_or_none(cls.phone_number == phone_number)
        
        # Якщо клієнт не знайдений, спробуємо знайти за номером телефону з "+" на початку
        if not client:
            client = cls.get_or_none(cls.phone_number == "+" + phone_number)

        if client:
            return {
                'id_client': client.id_client,
                'phone_number': client.phone_number,
                'name': client.name,
                'chat_id': client.chat_id
            }
        else:
            return None
        
    @classmethod
    def create_client(cls, phone_number, name, chat_id):
        """
        Створює нового клієнта, перевіряючи, чи він вже існує.

        :param phone_number: Номер телефону клієнта.
        :param name: Ім'я клієнта.
        :param chat_id: Айді чату клієнта
        :return: Айді існуючого клієнта або айді нового клієнта.
        """
        # Перевірка чи в номері телефону є "+" перед ним
        if not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        existing_client = cls.get_or_none(cls.phone_number == phone_number)
        if existing_client is None:
            new_client = cls.create(
                phone_number=phone_number,
                name=name,
                chat_id=chat_id
            )
            return new_client.id_client
        else:
            return existing_client.id_client

        
    class Meta:
        order_by = 'id_client'
        db_table = 'clients'


class Booking(BaseModel):
    """Запис"""

    id_booking = pw.AutoField()
    date_time = pw.DateTimeField(null=False)

    client_id = pw.ForeignKeyField(Client, backref='bookings')
    master_id = pw.ForeignKeyField(Master, backref='bookings')
    service_id = pw.ForeignKeyField(Service, backref='bookings')

    @classmethod
    def get_all_bookings(cls):
        """
        Отримує всі записи з бази даних.

        :return: Список записів з часом запису, ID клієнта, майстра та послуги.
        """
        all_bookings = []
        for booking in cls.select():
            all_bookings.append({
                'id_booking': booking.id_booking,
                'date_time': booking.date_time,
                'client_id': booking.client_id,
                'master_id': booking.master_id,
                'service_id': booking.service_id
            })
        return all_bookings

    @classmethod
    def get_bookings_for_client(cls, client_id):
        """
        Повертає інформацію про записи для певного клієнта.

        :param client_id: ID клієнта.
        :return: Список записів клієнта з часом запису, ID майстра та ID послуги.
        """
        client_bookings = []
        for booking in cls.select().where(cls.client_id == client_id):
            client_bookings.append({
                'date_time': booking.date_time,
                'master_id': booking.master_id,
                'service_id': booking.service_id
            })
        return client_bookings
    
    @classmethod
    def create_booking(cls, client_id, master_id, service_id, date_time):
        """
        Створює нове замовлення.

        :param client_id: ID клієнта.
        :param master_id: ID майстра.
        :param service_id: ID послуги.
        :param date_time: Дата та час замовлення.
        :return: Створене замовлення.
        """
        new_booking = cls.create(
            client_id=client_id,
            master_id=master_id,
            service_id=service_id,
            date_time=date_time
        )
        return new_booking
    
    @classmethod
    def get_master_bookings(cls, master_id):
        """
        Отримує список записів для конкретного майстра.

        :param master_id: ID майстра.
        :return: Список записів майстра.
        """
        master_bookings = []
        for booking in cls.select().where(cls.master_id == master_id):
            master_bookings.append({
                'id_booking': booking.id_booking,
                'date_time': booking.date_time,
                'client_id': booking.client_id,
                'master_id': booking.master_id,
                'service_id': booking.service_id
            })
        return master_bookings

    class Meta:
        order_by = 'id_booking'
        db_table = 'bookings'



class Schedule(BaseModel):
    """Розклад роботи майстрів"""

    date = pw.DateField(null=False)
    master_id = pw.ForeignKeyField(Master, backref='schedules')
    timetable = pw.CharField(max_length=255, default='{}', null=False)

    def set_timetable(self, timetable):
        """
        Встановлює розклад роботи у форматі JSON.

        :param timetable: Розклад роботи у форматі словника, який буде перетворено в JSON.
        """
        self.timetable = json.dumps(timetable)

    def update_schedule_for_date(self, new_timetable):
        """
        Оновлює розклад для певного дня.

        :param new_timetable: Новий розклад у форматі словника.
        :return: True, якщо розклад успішно оновлено, False, якщо розклад на цей день відсутній.
        """
        if not self:
            return False

        self.set_timetable(new_timetable)
        self.save()
        return True
    
    @classmethod
    def create_schedule_for_working_day(cls, master_id, date=None):
        """
        Створює розклад для майстра на наступний день.

        :param master: Майстер, для якого створюється розклад.
        :param date: Дата, для якої створюється розклад (за замовчуванням - наступний день).
        :return: True, якщо розклад успішно створено, False, якщо розклад для цього майстра на цю дату вже існує.
        """
        if date is None:
            date = datetime.date.today() + datetime.timedelta(days=1)
        
        existing_schedule = cls.select().where((cls.date == date) & (cls.master_id == master_id))
        if existing_schedule.exists():
            return False
        

        new_schedule = cls(date=date, master_id=master_id)
        new_schedule.set_timetable(Master.get_working_hours_by_id(master_id))
        new_schedule.save()
        return True
    
    @classmethod
    def create_schedule_for_weekend(cls, master_id, date=None):
        """
        Створює розклад для майстра на наступний день.

        :param master: Майстер, для якого створюється розклад.
        :param date: Дата, для якої створюється розклад (за замовчуванням - наступний день).
        :return: True, якщо розклад успішно створено, False, якщо розклад для цього майстра на цю дату вже існує.
        """
        if date is None:
            date = datetime.date.today() + datetime.timedelta(days=1)
        
        existing_schedule = cls.select().where((cls.date == date) & (cls.master_id == master_id))
        if existing_schedule.exists():
            return False
    
        schedule = {}
        for hour in range(start_hour, end_hour):
            for minute in range(0, 60, 60):  # По одній годині
                current_time = datetime.time(hour, minute)
                time_str = current_time.strftime("%H:%M")
                schedule[time_str] = "break"
        new_schedule = cls(date=date, master_id=master_id)
        new_schedule.set_timetable(schedule)
        new_schedule.save()
    
    @classmethod
    def get_schedule_for_date(cls, master_id, date):
        """
        Отримує розклад для конкретного майстра на певну дату.

        :param master: Майстер, для якого потрібно отримати розклад.
        :param date: Дата, для якої потрібно отримати розклад.
        :return: Розклад для майстра на задану дату, або None, якщо розклад не знайдено.
        """
        schedule = cls.select().where((cls.date == date) & (cls.master_id == master_id)).first()
        if schedule:
            return json.loads(schedule.timetable)
        return None
    
    @classmethod
    def get_all_slots(cls, master_id, date):
        """
        Отримує всі слоти для конкретного майстра на певну дату.

        :param master: Майстер, для якого потрібно отримати доступні слоти.
        :param date: Дата, для якої потрібно отримати доступні слоти.
        :return: Три списки з годинами booked_slots, break_slots, available_slots
        """
        # Отримуємо розклад для майстра на задану дату
        schedule = cls.get_schedule_for_date(master_id, date)
        if not schedule:
            return []  # Якщо розклад не знайдено, повертаємо порожній список доступних слотів

        booked_slots = [time for time, status in schedule.items() if status == 'booked']
        break_slots = [time for time, status in schedule.items() if status == 'break']
        available_slots = [time for time, status in schedule.items() if status == 'available']

        return booked_slots, break_slots, available_slots

    @classmethod
    def get_available_slots(cls, master_id, date):
        """
        Отримує доступні для бронювання слоти для конкретного майстра на певну дату.

        :param master: Майстер, для якого потрібно отримати доступні слоти.
        :param date: Дата, для якої потрібно отримати доступні слоти.
        :return: Список доступних для бронювання слотів у форматі [час1, час2, ...].
        """
        # Отримуємо розклад для майстра на задану дату
        schedule = cls.get_schedule_for_date(master_id, date)
        if not schedule:
            return []  # Якщо розклад не знайдено, повертаємо порожній список доступних слотів

        available_slots = [time for time, status in schedule.items() if status == 'available']

        return available_slots
    
    @classmethod
    def get_days_with_schedule(cls, master_id):
        """
        Отримує список днів, на які у майстра є розклад.

        :param master: Майстер, для якого потрібно отримати список днів з розкладом.
        :return: Список днів з розкладом у форматі ["YYYY-MM-DD", "YYYY-MM-DD", ...].
        """
        days_with_schedule = []
        schedules = cls.select().where(cls.master_id == master_id)
        for schedule in schedules:
            days_with_schedule.append(schedule.date.strftime("%Y-%m-%d"))
        return days_with_schedule
    
    @classmethod
    def get_available_days_with_schedule(cls, master_id):
        """
        Отримує список днів, на які у майстра є розклад з хоча б одним доступним слотом.
    
        :param master_id: Ідентифікатор майстра, для якого потрібно отримати список днів з доступними слотами.
        :return: Список днів з доступними слотами у форматі ["YYYY-MM-DD", "YYYY-MM-DD", ...].
        """
        days_with_schedule = []
        schedules = cls.select().where(cls.master_id == master_id)
        for schedule in schedules:
            # Отримуємо доступні слоти для поточного розкладу
            available_slots = cls.get_available_slots(schedule.master_id, schedule.date)
            # Якщо є доступні слоти, додаємо день до списку
            if available_slots:
                days_with_schedule.append(schedule.date.strftime("%Y-%m-%d"))
        return days_with_schedule
    
    @classmethod
    def book_slot(cls, master_id, date_time):
        """
        Встановлює статус для певного слоту на 'booked'.

        :param master_id: ID майстра.
        :param date_time: Дата та час слоту у форматі datetime.
        :return: None
        """
        date = date_time.date()
        time_str = date_time.strftime("%H:%M")
        schedule = cls.get_or_none((cls.master_id == master_id) & (cls.date == date))
        if schedule:
            timetable = json.loads(schedule.timetable)
            if time_str in timetable:
                timetable[time_str] = 'booked'
                schedule.set_timetable(timetable)
                schedule.save()

    @classmethod
    def cancel_booking(cls, master_id, date_time):
        """
        Видаляє бронювання для певного слоту.

        :param master_id: ID майстра.
        :param date_time: Дата та час слоту у форматі datetime.
        :return: None
        """
        date = date_time.date()
        time_str = date_time.strftime("%H:%M")
        schedule = cls.get_or_none((cls.master_id == master_id) & (cls.date == date))
        if schedule:
            timetable = json.loads(schedule.timetable)
            if time_str in timetable:
                timetable[time_str] = 'available'
                schedule.set_timetable(timetable)
                schedule.save()

    class Meta:
        db_table = 'schedules'

def create_tables():
    with db:
        db.create_tables([Admin, Booking, Master, Client, Service, Service_has_Master])
        db.create_tables([Schedule])

# create_tables()