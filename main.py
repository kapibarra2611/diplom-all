from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from random import randrange
import requests
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import threading
import database
import database as db
import re
from config import USER_TOKEN, GROUP_TOKEN, GROUP_ID


class VkUser:
    """Класс, использующий токен пользователя, для получения информации при помощи VK API."""

    def __init__(self, id):
        self.user_id = id

    def get_params(self, add_params: dict = None):

        """Возвращает параметры для соответствующего метода API.
        Подробнее в документации VK API <https://dev.vk.com/api/api-requests>.
        :param add_params: Входные параметры. Опционально.
        :type add_params: dict
               """
        params = {
            'access_token': USER_TOKEN,
            'v': '5.131'
        }
        if add_params:
            params.update(add_params)
            pass
        return params

    def get_user_data(self, user_id):

        """
        Подробнее в документации VK API <https://dev.vk.com/method/users.get>.
        :param user_id: Идентификатор пользователя vk.
        :type user_id: int
               """
        try:
            user_data = vk_user.method('users.get', {'user_ids': user_id, 'fields': 'sex, city, bdate'})
        except requests.exceptions.RequestException:
            print(f"Не удалось получить данные пользователя для {user_id}")
            VkBot().write_msg(user_id, 'Ошибка с нашей стороны. Попробуйте позже.')
            exit()
        user_bdate = int(user_data[0]['bdate'][6:10]) if user_data[0]['bdate'][6:10] else None
        user_city = user_data[0]['city']['id'] if user_data[0]['city']['id'] else None
        user_sex = user_data[0]['sex'] if user_data[0]['sex'] else None

        return user_bdate, user_city, user_sex

    def get_city(self, city):
        """Возвращает идентификатор города.
        Подробнее в документации VK API <https://dev.vk.com/method/database.getCities>.
        :param city: Город, полученный в сообщении от пользователя вк.
        :type city: str
               """
        response = requests.get(
            'https://api.vk.com/method/database.getCities',
            self.get_params({'country_id': 1, 'count': 1, 'q': city})
        )

        try:
            response = response.json()['response']['items']
            if not response:
                # VkBot().write_msg(user_id, 'Город не найден')
                city = False
            else:
                for city_id in response:
                    city = city_id['id']
            return city

        except requests.exceptions.RequestException:
            print(f"Не удалось получить город пользователя для {user_id}: {response.json()['error']['error_msg']}")
            VkBot().write_msg(user_id, 'Ошибка с нашей стороны. Попробуйте позже.')

            city = False
            return city

    def get_top_photos(self, partner_id):
        """Возвращает список из ссылок на три самые популярные фотографии пользователя.
        Подробнее в документации VK API <https://dev.vk.com/method/photos.get>.
       :param partner_id: Идентификатор пользователя vk.
       :type partner_id: int
       """
        photos = []
        response = requests.get(
            'https://api.vk.com/method/photos.get',
            self.get_params({'owner_id': partner_id,
                             'album_id': 'profile',
                             'extended': 1,
                             'count': 255}
                            )
        )
        try:
            sorted_response = sorted(response.json()['response']['items'],
                                     key=lambda x: x['likes']['count'], reverse=True)
            for photo_id in sorted_response:
                photos.append(f'''photo{partner_id}_{photo_id['id']}''')
            top_photos = ','.join(photos[:3])
            return top_photos
        except requests.exceptions.RequestException:
            print(f"Не удалось получить список фотографий для {user_id}: {response.json()['error']['error_msg']}")
            VkBot().write_msg(user_id, 'Ошибка с нашей стороны. Попробуйте позже.')

            return False

    def find_partner(self, bdate, sex, city, offset):
        """Метод для поиска потенциального партнера в вк и добавление его в базу данных.
        Подробнее в документации VK API <https://dev.vk.com/method/users.search>.
        """
        sex_find = (1 if sex == 1 else 2)

        response = vk_user.method('users.search', {'count': 5,
                                                   'offset': offset,
                                                   'city': city,
                                                   'country': 1,
                                                   'sex': sex_find,
                                                   'age_from': bdate - 5,
                                                   'age_to': bdate + 5,
                                                   'fields': 'is_closed',
                                                   'status': 6,
                                                   'has_photo': 1})

        for item in response['items']:
            if item['is_closed']:
                continue
            database.add_user(item['id'])

        searcher = db.session.get(database.Searcher, self.user_id)
        if not searcher:
            searcher = database.Searcher(vk_id=self.user_id)
        searcher.offset = offset

        db.session.add(searcher)
        db.session.commit()

    def get_partner_from_db(self):
        partner = database.pop_user()

        if partner:
            user = vk_user.method('users.get', {'user_ids': partner.vk_id})[0]
            VkBot().offer_partner(user['id'], user['first_name'], user['last_name'])

        else:
            searcher = db.session.get(database.Searcher, self.user_id)
            searcher.offset += 5
            db.session.add(searcher)
            db.session.commit()
            self.find_partner(searcher.bdate, searcher.sex, searcher.city, searcher.offset)
            self.get_partner_from_db()


class VkBot:
    """Класс, использующий токен группы, для общения с пользователем."""

    def __init__(self):
        self.commands = [['привет', 'прив', 'ghbdtn', 'hi', 'hello', 'здравствуйте', 'хай'],
                         ['старт', 'поехали', 'начать', 'го', 'go', 'start'],
                         ['пока', 'bye', 'до свидания', 'gjrf', 'выход'],
                         ['далее']]

    def write_msg(self, user_id, message, attachment='', **kwargs):
        """Отправить сообщение пользователю.

        Подробнее в документации VK API <https://dev.vk.com/method/messages.send>.

        :param user_id: Идентификатор пользователя vk, которому отправляется сообщение.
        :type user_id: int
        :param message: Текст личного сообщения. Обязательный параметр, если не задан параметр attachment
        :type message: str
        :param attachment: Медиавложения к личному сообщению, перечисленные через запятую.
        Каждое вложение представлено в формате: <type><owner_id>_<media_id>
        :type attachment: str
        :param kwargs: Объекты, описывающие специальные сообщения. Например, клавиатуру.
        """

        vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7),
                                    'attachment': attachment, **kwargs})

    def chat_keyboard(self, buttons, button_colors):
        """Метод создания новой клавиатуры для бота.

        Подробнее в документации VK API <https://dev.vk.com/api/bots/development/keyboard>.

        :param buttons: Список кнопок.
        :type buttons: list
        :param button_colors: Список цветов кнопок.
        :type button_colors: list
        """
        keyboard = VkKeyboard.get_empty_keyboard()
        keyboard = VkKeyboard(one_time=True)
        for btn, btn_color in zip(buttons, button_colors):
            keyboard.add_button(btn, btn_color)
        return keyboard

    def offer_partner(self, partner_id, first_name, last_name):
        """Отправить пользователю потенциального партнера и его фотографии.

        :param partner_id: Идентификатор партнера в vk.
        :type partner_id: int
        :param first_name: Имя партнера.
        :type first_name: str
        :param last_name: Фамилия партнера.
        :type last_name: str
        """

        message = f'{first_name} {last_name}\n' \
                  f'Ссылка: @id{partner_id}'

        user_photos = VkUser(user_id).get_top_photos(partner_id)

        if user_photos:
            buttons = ['Далее']
            button_colors = [VkKeyboardColor.SECONDARY]
            keyboard = self.chat_keyboard(buttons, button_colors)
            self.write_msg(user_id, message, user_photos, keyboard=keyboard.get_keyboard())

    def processing_messages(self, user_id, message_text):
        """Основной метод обработки сообщений пользователя.

        :param user_id: Идентификатор пользователя vk.
        :type user_id: int
        :param message_text: Сообщение пользователя.
        :type message_text: str
        """

        regex = r"^\d{4}$"

        if message_text in self.commands[2]:
            self.write_msg(user_id, 'good_bye')
            return

        if message_text in self.commands[1]:
            bdate, sex, city = VkUser(user_id).get_user_data(user_id)
            sex_print = 'Мужской' if sex == 1 else 'Женский'
            self.write_msg(user_id, f'Ищем пару с заданными параметрами: Год рождения: {bdate}+-5, '
                                    f'Пол: {sex_print}, Город: {city}')
            VkUser(user_id).find_partner(bdate, sex, city, offset=0)
            VkUser(user_id).get_partner_from_db()
            return

        elif message_text in self.commands[0]:
            buttons = ['Старт']
            button_colors = [VkKeyboardColor.POSITIVE]
            keyboard = self.chat_keyboard(buttons, button_colors)
            bdate, sex, city = VkUser(user_id).get_user_data(user_id)
            db.fill_searcher(user_id, bdate, sex, city)
            self.write_msg(user_id, 'Привет, я бот, который умеет искать пару', keyboard=keyboard.get_keyboard())

            if not bdate:
                self.write_msg(user_id, 'Введите год рождения в формате "1982"')
                searcher = db.session.query(database.Searcher).get(user_id)
                searcher.step = 0
                db.session.add(searcher)
                db.session.commit()
                return

            if not sex:
                self.write_msg(user_id, 'Введите пол (мужской/женский')
                searcher = db.session.query(database.Searcher).get(user_id)
                searcher.step = 1
                db.session.add(searcher)
                db.session.commit()
                return

            if not city:
                self.write_msg(user_id, 'Введите город')
                searcher = db.session.query(database.Searcher).get(user_id)
                searcher.step = 2
                db.session.add(searcher)
                db.session.commit()
                return

        elif message_text in self.commands[3]:
            VkUser(user_id).get_partner_from_db()
            return

        elif re.match(regex, message_text):
            searcher = db.session.query(database.Searcher).get(user_id)
            searcher.bdate = int(message_text)
            db.session.add(searcher)
            db.session.commit()
            self.write_msg(user_id, 'Год рождения сохранен')
            return

        elif message_text.lower() in ['мужчина', 'женщина']:
            if message_text.lower() == 'мужчина':
                sex_id = 1
            else:
                sex_id = 2

            searcher = db.session.query(database.Searcher).get(user_id)
            searcher.sex = sex_id

            db.session.add(searcher)
            db.session.commit()
            self.write_msg(user_id, 'Пол сохранен')
            return

        else:
            city = VkUser(user_id).get_city(message_text)
            if not city:
                self.write_msg(user_id, 'Неизвестная команда')
                return
            searcher = db.session.query(database.Searcher).get(user_id)
            searcher.city = city

            db.session.add(searcher)
            db.session.commit()
            self.write_msg(user_id, 'Город сохранен')

            return


if __name__ == '__main__':

    vk_user = vk_api.VkApi(token=USER_TOKEN)
    vk = vk_api.VkApi(token=GROUP_TOKEN)

    db.create_tables()
    try:
        longpoll = VkBotLongPoll(vk, GROUP_ID)

        while True:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
                    user_id = event.object.message['from_id']
                    message = event.object.message['text']
                    thread = threading.Thread(target=VkBot().processing_messages, args=(user_id, message.lower()))
                    thread.start()
    except vk_api.exceptions.ApiError as error_msg:
        print(error_msg)
