from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from random import randrange
import requests
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import threading
import database
import database as db
from config import USER_TOKEN, GROUP_TOKEN, GROUP_ID


class VkUser:
    """Класс, использующий токен пользователя, для получения информации при помощи VK API."""

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
        user_data = vk_user.method('users.get', {'user_ids': user_id, 'fields': 'sex, city, bdate'})
        user_bdate = int(user_data[0]['bdate'][6:10])
        user_city = user_data[0]['city']['id']
        user_sex = user_data[0]['sex']

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
                VkBot().write_msg(user_id, 'Город не найден')
                city = False
            else:
                for city_id in response:
                    city = city_id['id']
        except:
            print(f"Не удалось получить город пользователя для {user_id}: {response.json()['error']['error_msg']}")
            VkBot().write_msg(user_id, 'Ошибка с нашей стороны. Попробуйте позже.')
            # db.update(user_id, db.UserPosition, position=1, offset=0)
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
        except:
            print(f"Не удалось получить список фотографий для {user_id}: {response.json()['error']['error_msg']}")
            VkBot().write_msg(user_id, 'Ошибка с нашей стороны. Попробуйте позже.')

            return False

    def find_partner(self, bdate, sex, city):
        """Метод для поиска потенциального партнера в вк и добавление его в базу данных.
        Подробнее в документации VK API <https://dev.vk.com/method/users.search>.
        """
        sex_find = (1 if sex == 1 else 2)

        response = vk_user.method('users.search', {'count': 3,
                                                   'offset': 0,
                                                   'city': city,
                                                   'country': 1,
                                                   'sex': sex_find,
                                                   'age_from': bdate - 5,
                                                   'age_to': bdate + 5,
                                                   'fields': 'is_closed',
                                                   'status': 6,
                                                   'has_photo': 1})

        for item in response['items']:
            user_photos = vk_user.method('photos.get', {'owner_id': item['id'],
                                                        'album_id': 'profile',
                                                        'extended': 1,
                                                        'count': 255})

            sorted_response = sorted(user_photos['items'],
                                     key=lambda x: x['likes']['count'], reverse=True)

            photos_message = []
            for photo in sorted_response[:3]:
                for element in photo['sizes']:
                    if element['type'] == 'x':
                        photos_message.append(element['url'])
            add_user = database.add_user(item['id'], item['first_name'], item['last_name'], photos_message)
            print(add_user)
            VkBot().offer_partner(item['id'], item['first_name'], item['last_name'])


class VkBot:
    """Класс, использующий токен группы, для общения с пользователем."""

    def __init__(self):
        self.commands = [['привет', 'прив', 'ghbdtn', 'hi', 'hello', 'здравствуйте', 'хай'],
                         ['старт', 'поехали', 'начать', 'го', 'go', 'start'],
                         ['пока', 'bye', 'до свидания', 'gjrf', 'выход']]

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
        try:
            vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7),
                                        'attachment': attachment, **kwargs})
        except Exception as e:
            print(e)

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
        db_user = database.get_user(partner_id)
        message = f'{first_name} {last_name}\n' \
                  f'Ссылка: @id{partner_id}'

        top_photos = ''
        for photo in db_user.photos:
            top_photos += photo.url + ','
        print(top_photos)

        if top_photos:
            buttons = ['Далее']
            button_colors = [VkKeyboardColor.SECONDARY]
            keyboard = self.chat_keyboard(buttons, button_colors)
            self.write_msg(user_id, message, top_photos, keyboard=keyboard.get_keyboard())

        else:
            return

    def processing_messages(self, user_id, message_text):
        """Основной метод обработки сообщений пользователя.

        :param user_id: Идентификатор пользователя vk.
        :type user_id: int
        :param message_text: Сообщение пользователя.
        :type message_text: str
        """

        if message_text in self.commands[2]:
            self.write_msg(user_id, 'good_bye')
            return

        if message_text in self.commands[1]:
            bdate, sex, city = VkUser().get_user_data(user_id)
            sex_print = 'Мужской' if sex == 1 else 'Женский'
            self.write_msg(user_id, f'Ищем пару с заданными параметрами: Год рождения: {bdate}+-5, '
                                    f'Пол: {sex_print}, Город: {city}')
            VkUser().find_partner(bdate, sex, city)
            return

        elif message_text in self.commands[0]:
            buttons = ['Старт']
            button_colors = [VkKeyboardColor.POSITIVE]
            keyboard = self.chat_keyboard(buttons, button_colors)
            self.write_msg(user_id, 'Привет, я бот, который умеет искать пару', keyboard=keyboard.get_keyboard())

        #     todo: Добавить offset

        else:
            self.write_msg(user_id, 'Неизвестная команда')


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
