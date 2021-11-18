import json
from typing import Dict, Any, Optional, Union, Tuple

import requests
import re

from loader import rapidapi_connect
from loader import logger
from telebot import types
from history import save_history


@logger.catch
class API_request:

    def __init__(self) -> None:
        self.status: int = 0
        self.group_city: Optional[Dict[str, Any]] = None
        self.city: Optional[Dict[str, Any]] = None
        self.destination_id: str = ''
        self.number_hotels: int = 0
        self.price: Dict[str, int] = dict()
        self.distance: Dict[str, float] = dict()
        self.date_range: Dict[str, Union[str, int]] = dict()
        self.hotels: Optional[Dict[str, Any]] = None
        self.number_photo: Optional[int] = None
        self.photos: Optional[Dict[str, Any]] = None
        self.locale: Dict[str, str] = dict()

    def action_locale(self, action, lang_user='en_US', distance='miles', currency='USD', currency_str='$') -> \
            Tuple[str, str, str]:
        """
        Функция для сохранения и чтения локальных параметров запроса
        :param action: 'save' для записи локальных параметров, иначе загрузка
        :param lang_user: язык ввода
        :param distance: км или мили для измерения расстояния
        :param currency: обозначение валюты
        :param currency_str: строковое представление валюты
        :return:
        """
        if action == 'save':
            self.locale['locale'] = lang_user
            self.locale['distance'] = distance
            self.locale['currency'] = currency
            self.locale['currency_str'] = currency_str
        else:
            lang_user = self.locale['locale']
            currency = self.locale['currency']
            currency_str = self.locale['currency_str']
            return lang_user, currency, currency_str

    def search_cities(self, message: 'telebot.types.Message', bot: 'telebot.TeleBot', user_list: Dict[int, 'User'],
                      from_user: int) -> None:
        """
        Функция поиска городов в зависимости от локальных параметров и сохранение результата в group_city
        :param message: сообщение пользователя
        :param bot: сам бот
        :param user_list: список пользователей
        :param from_user: id пользователя
        :return: None
        """
        city = message.text
        city_group = self.group_city
        if not city_group:
            detect = re.sub(r'[\Wа-яА-ЯёЁ]+', "ru", city)
            action = 'save'
            lang_user = 'en_US'
            if detect == 'ru':
                lang_user = 'ru_RU'
                bot.send_message(from_user,
                                 'Начат поиск города {city} на русском языке. Подождите...'.format(city=city))
                self.action_locale(action, lang_user=lang_user, distance='км', currency='RUB', currency_str='руб.')
            else:
                bot.send_message(from_user, 'Начат поиск города {city} . Подождите... '.format(city=city))
                self.action_locale(action)
            querystring = {"query": city, "locale": lang_user}
            logger.info('Поиск города {city}: команда {comm}, пользователь id:{id}'.format(
                city=city, comm=user_list[from_user].command, id=from_user))
            response = requests.request("GET", rapidapi_connect['url_city'], headers=rapidapi_connect['headers'],
                                        params=querystring, timeout=60)
            logger.info('Ответ получен response.status_code = {response}: команда {comm}, пользователь id:{id}'.format(
                response=response.status_code, city=city, comm=user_list[from_user].command, id=from_user))
            if response.status_code == 200:
                data = json.loads(response.text)
                suggestions = list(filter(lambda i_city: i_city['group'] == 'CITY_GROUP', data['suggestions']))[0][
                    'entities']
                city_group = list(filter(lambda i_name: i_name['type'] == 'CITY', suggestions))
            else:
                logger.info('response.status_code != 200. Сервер не отвечает. Город не найден.')
                bot.send_message(from_user, 'Сервер не отвечает. Город не найден.')
                self.status = 0
                self.end_query(bot, user_list, from_user)
        if len(city_group) > 0:
            logger.info('Найдено {number} городов: команда {comm}, пользователь id:{id}'.format(number=len(city_group),
                                                                                                comm=user_list[
                                                                                                    from_user].command,
                                                                                                id=from_user))
            for i_key, i_value in enumerate(city_group):
                i_name = re.sub(r'\<.*?\>', "", i_value['caption'])
                i_value['long_name'] = i_name
            self.group_city = city_group
            user_keyboard(bot, user_list, from_user)
        else:
            self.status -= 1
            logger.info('города {name} не найдено: команда {comm}, status={status} пользователь id:{id}'.format(
                name=city, comm=user_list[from_user].command, status=self.status, id=from_user))
            bot.send_message(from_user, 'города {name} не найдено'.format(name=city))
            bot.send_message(from_user, 'Введите город, в котором будет проводиться поиск')

    def search_hotels(self, bot: 'telebot.TeleBot', user_list: Dict[int, 'User'],
                      from_user: int, sort_order: str) -> None:
        """
        Функция поиска отелей в выбранном городе и сохранение результата в hotels
        :param bot: сам бот
        :param user_list: список пользователей
        :param from_user: id пользователя
        :param sort_order: метод сортировки результатов
        :return: None
        """
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = self.city
        checkIn_day = self.date_range['checkIn_day']
        checkOut_day = self.date_range['checkOut_day']
        action = 'load'
        lang_user, currency, currency_str = self.action_locale(self, action)
        querystring = {"destinationId": current_city['destinationId'], "pageNumber": "1",
                       "pageSize": self.number_hotels, "checkIn": checkIn_day,
                       "checkOut": checkOut_day, "adults1": "1", "sortOrder": sort_order, "locale": lang_user,
                       "currency": currency
                       }
        response = requests.request("GET", rapidapi_connect['url_hotels'], headers=rapidapi_connect['headers'],
                                    params=querystring, timeout=60)
        if response.status_code == 200:
            data = json.loads(response.text)
            self.hotels = data['data']['body']['searchResults']['results']

            if len(self.hotels) > 0:
                for num, hotel in enumerate(self.hotels, 1):
                    i_hotel = self.hotel_information(self, hotel, num, currency_str)
                    bot.send_message(from_user, i_hotel)
                    if self.number_photo:
                        self.search_hotel_photo(bot, user_list, from_user, hotel['id'])
            else:
                bot.send_message(from_user, 'Отелей в указанном городе не найдено')
            self.end_query(bot, user_list, from_user)
        else:
            logger.info('response.status_code != 200. Сервер не отвечает. Отели не найдены.')
            bot.send_message(from_user, 'Сервер не отвечает. Отели не найдены.')
            self.status -= 1
            self.end_query(bot, user_list, from_user)

    def search_best_hotels(self, bot: 'telebot.TeleBot', user_list: Dict[int, 'User'],
                           from_user: int, sort_order: str) -> None:
        """
        Функция поиска отелей в выбранном городе для команды /bestdeal и сохранение результата в hotels
        :param bot: сам бот
        :param user_list: список пользователей
        :param from_user: id пользователя
        :param sort_order: метод сортировки результатов
        :return: None
        """
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = self.city
        checkIn_day = self.date_range['checkIn_day']
        checkOut_day = self.date_range['checkOut_day']
        action = 'load'
        lang_user, currency, currency_str = self.action_locale(self, action)
        self.hotels = []
        pageNumber = 1
        find_number = 0
        price_min = self.price['min']
        price_max = self.price['max']
        check_delta_days = self.date_range['delta_days']
        if currency == 'RUB':
            price_min = price_min * check_delta_days
            price_max = price_max * check_delta_days
        while len(self.hotels) < self.number_hotels:
            if pageNumber <= 10:
                bot.send_message(from_user, 'Подождите, идет поиск вариантов. выполняем запрос № ' + str(pageNumber))
                querystring = {"destinationId": current_city['destinationId'], "pageNumber": pageNumber,
                               "pageSize": "25",
                               "checkIn": checkIn_day, "checkOut": checkOut_day, "adults1": "1",
                               "priceMin": price_min,
                               "priceMax": price_max,
                               "sortOrder": sort_order, "locale": lang_user, "currency": currency}
                logger.info('Поиск отелей /bestdeal querystring={querystring}'.format(querystring=querystring))
                response = requests.request("GET", rapidapi_connect['url_hotels'], headers=rapidapi_connect['headers'],
                                            params=querystring, timeout=60)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    if len(data['data']['body']['searchResults']['results']) > 0:
                        for num, hotel in enumerate(data['data']['body']['searchResults']['results'], 1):
                            if len(self.hotels) < self.number_hotels:
                                if hotel.get('landmarks')[0].get('distance'):
                                    i_landmarks = float(
                                        re.sub(',', '.', hotel['landmarks'][0]['distance'].split(' ')[0]))
                                    if self.distance['min'] <= i_landmarks <= \
                                            self.distance['max']:
                                        self.hotels.append(hotel)
                                        find_number += 1
                                        i_hotel = self.hotel_information(self, hotel, find_number, currency_str)
                                        bot.send_message(from_user, i_hotel)
                                        if self.number_photo:
                                            self.search_hotel_photo(bot, user_list, from_user, hotel['id'])
                            else:
                                break
                else:
                    logger.info('response.status_code != 200. Сервер не отвечает. Отели для bestdeal не найдены.')
                    bot.send_message(from_user, 'Сервер не отвечает. Отели для bestdeal не найдены')
                    self.status -= 1
                    self.end_query(bot, user_list, from_user)
                pageNumber += 1
            else:
                bot.send_message(from_user, 'Просмотрено более 250 вариантов, поиск прекращен')
                break
        if len(self.hotels) == 0:
            bot.send_message(from_user, 'Отелей в указанном городе не найдено')
        self.end_query(bot, user_list, from_user)

    def search_hotel_photo(self, bot: 'telebot.TeleBot', user_list: Dict[int, 'User'], from_user: int,
                           id_hotel: str) -> None:
        """
        Функция поиска фотографий в выбранном отеле и сохранение результата в photos
        :param bot: сам бот
        :param user_list: список пользователей
        :param from_user: id пользователя
        :param id_hotel: id отеля
        :return: None
        """
        querystring = {"id": id_hotel}
        response = requests.request("GET", rapidapi_connect['url_photo'], headers=rapidapi_connect['headers'],
                                    params=querystring, timeout=60)
        if response.status_code == 200:
            data = json.loads(response.text)
            self.photos = data.get('hotelImages')
            media_group = list()
            if len(self.photos) > 0:
                for num, photo in enumerate(self.photos, 1):
                    if num <= self.number_photo:
                        media_group.append(types.InputMediaPhoto(media=re.sub('{size}', "z", photo.get('baseUrl'))))
            bot.send_media_group(from_user, media=media_group)
        else:
            logger.info('response.status_code != 200. Сервер не отвечает. Фото не найдены.')
            bot.send_message(from_user, 'Сервер не отвечает. Фото не найдены')
            self.status -= 1
            self.end_query(bot, user_list, from_user)

    @staticmethod
    def hotel_information(self, hotel: Dict[str, Any], find_number: int, currency_str: str) -> str:
        """
        Функция сбора данных об отеле для вывода пользователю
        :param self: текущий запрос
        :param hotel: словарь с данными об отеле
        :param find_number: порядковый номер найденного отеля
        :param currency_str: строкое представление валюты
        :return: str
        """
        address_list = [x for x in
                        [hotel['address'].get('streetAddress', ''),
                         hotel['address'].get('extendedAddress', ''),
                         hotel['address'].get('locality', ''),
                         hotel['address'].get('postalCode', ''),
                         hotel['address'].get('region', '')] if x != '']
        address = ', '.join(address_list)
        i_date = self.date_range['checkIn_day'].split('-')
        checkIn_day = '{d}.{m}.{Y}'.format(d=i_date[2], m=i_date[1], Y=i_date[0])
        i_date = self.date_range['checkOut_day'].split('-')
        checkOut_day = '{d}.{m}.{Y}'.format(d=i_date[2], m=i_date[1], Y=i_date[0])
        check_delta_days = self.date_range['delta_days']
        price_day = hotel['ratePlan']['price']['exactCurrent']
        price_all = price_day
        if currency_str == 'USD':
            price_all = round(price_all * check_delta_days, 2)
        else:
            price_day = round(price_day / check_delta_days, 2)
        str_price_day = 'Стоимость проживания за сутки: {price_day} {currency_str}'.format(price_day=price_day,
                                                                                           currency_str=currency_str)
        str_price_all = 'Стоимость проживания за {check_delta_days} дня (суток) с {checkIn_day} по {checkOut_day}: ' \
                        '{price_all} {currency_str}'.format(check_delta_days=check_delta_days, checkIn_day=checkIn_day,
                                                            checkOut_day=checkOut_day, price_all=price_all,
                                                            currency_str=currency_str)
        landmarks = 'Расстояние от центра города - {r}'.format(r=hotel['landmarks'][0]['distance'])
        site = 'https://ru.hotels.com/ho' + str(hotel['id'])
        hotel_info = '{num}. {name}.  Рейтинг отеля:{rating} Адрес: {address}.\n' \
                     '{str_price_day}\n{str_price_all}\nРасстояние - {landmarks}\n Сайт: {hotel_site}\n'.format(
                        num=find_number, name=hotel['name'],
                        rating='\U00002B50' * int(hotel['starRating']),
                        address=address,
                        str_price_day=str_price_day, str_price_all=str_price_all,
                        currency_str=currency_str, landmarks=landmarks,
                        hotel_site=site)
        return hotel_info

    def end_query(self, bot: 'telebot.TeleBot', user_list: Dict[int, 'User'], from_user: int,
                  end_message='Запрос выполнен, введите другую команду ') -> bool:
        """
        Функция завершения запроса и сохранения его в истории
        :param bot: сам бот
        :param user_list: список пользователей
        :param from_user: id пользователя
        :param end_message: сообщение для пользователя
        :return: bool
        """
        bot.send_message(from_user, end_message)
        user_list[from_user].query.status = 15
        res = save_history(self, user_list, from_user)
        if res:
            user_list[from_user].command = ""
        bot.send_message(from_user,
                         'Команды бота:\n'
                         '/lowprice — вывод самых дешёвых отелей в городе\n'
                         '/highprice — вывод самых дорогих отелей в городе\n'
                         '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                         '/history - история поиска\n')
        return True


@logger.catch
def user_keyboard(bot: 'telebot.TeleBot', user_list: Dict[int, 'User'], from_user: int) -> None:
    """
    Функция вывода клавиатуры с возможными вариантами найденных городов
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    keyboard = types.InlineKeyboardMarkup()
    for i_key, i_value in enumerate(user_list[from_user].query.group_city):
        keyboard.add(
            types.InlineKeyboardButton(text=i_value['long_name'], callback_data='city_' + i_value['destinationId']))
    keyboard.add(types.InlineKeyboardButton(text='Города нет в списке, повторить ввод',
                                            callback_data='city_' + 'repeat'))
    question = 'Выберите город из списка'
    bot.send_message(from_user, text=question, reply_markup=keyboard)
