import datetime
import json
import requests
import re
from typing import Dict, List, Any, Union
from requests import ReadTimeout
from loader import rapidapi_connect, db, History_db, logger
from telebot import types, TeleBot
from telebot.types import Message
from rapidapi import API_request


class User:
    """
    класс Пользователь. Хранит текущий запрос, а также историю запросов
    Свойства:
    command: str: команда пользователя
    query: API_request: экземпляр класса, хранит сведения о текущем запросе
    history: Dict[str, List[Union[str, API_request]]]: Словарь для временного хранения истории запросов пользователя.
             ключ: дата и время запроса, значение: список из выполненной команды и самого выполненного запроса
    """

    def __init__(self) -> None:
        self.command: str = ''
        self.query: API_request = API_request()
        self.history: Dict[str, List[Union[str, API_request]]] = dict()

    def reset_query(self):
        self.query = API_request()

    def search_cities(self, message: Message, bot: TeleBot, from_user: int) -> bool:
        """
        Метод поиска городов в зависимости от локальных параметров и сохранение результата в group_city
        :param message: сообщение пользователя
        :param bot: сам бот
        :param from_user: id пользователя
        :return: bool
        """
        city = message.text
        logger.info(self.query.status)
        city_group = self.query.group_city
        if not self.query.group_city:

            detect = re.sub(r'[\Wа-яА-ЯёЁ]+', "ru", city)
            action = 'save'
            if detect == 'ru':
                lang_user = 'ru_RU'
                bot.send_message(from_user,
                                 'Начат поиск города {city} на русском языке. Подождите...'.format(city=city))
                self.query.action_locale(action, lang_user=lang_user, distance='км',
                                         currency='RUB', currency_str='руб.')
            else:
                bot.send_message(from_user, 'Начат поиск города {city} . Подождите... '.format(city=city))
                self.query.action_locale(action)
            lang_user, currency, currency_str = self.query.action_locale(self.query, action)
            querystring = {"query": city, "locale": lang_user, "currency": currency}
            logger.info('Поиск города {city}: команда {comm}, пользователь id:{id}'.format(
                city=city, comm=self.command, id=from_user))

            try:
                response = requests.request("GET", rapidapi_connect['url_city'], headers=rapidapi_connect['headers'],
                                            params=querystring, timeout=30)
                logger.info(
                    'Ответ получен response.status_code = {response}: команда {comm}, пользователь id:{id}'.format(
                        response=response.status_code, city=city, comm=self.command, id=from_user))
                if response.status_code == 200:
                    data = json.loads(response.text)
                    suggestions = list(filter(lambda i_city: i_city['group'] == 'CITY_GROUP', data['suggestions']))[0][
                        'entities']
                    city_group = list(filter(lambda one_name: one_name['type'] == 'CITY', suggestions))
                    logger.info('city_group={data}'.format(data=str(city_group)))
                    logger.info('len(city_group)={data}'.format(data=len(city_group)))
                else:
                    logger.info('response.status_code != 200. Сервер не отвечает. Город не найден.')
                    end_message = 'Сервер не отвечает. Город не найден.'
                    self.query.status = 0
                    self.end_query(bot, from_user, end_message)
                    return False

            except ReadTimeout:
                end_message = 'Время ожидания ответа сервера истекло. Город {city} не найден.'.format(city=city)
                logger.info('{end_message} Команда {comm}, пользователь id:{id}'.format(
                    end_message=end_message, comm=self.command, id=from_user))
                self.query.status = 0
                self.end_query(bot, from_user, end_message)
                return False
        if city_group and (len(city_group) > 0):
            logger.info('Найдено {number} городов: команда {comm}, пользователь id:{id}'.format(number=len(city_group),
                                                                                                comm=self.command,
                                                                                                id=from_user))
            logger.info('query.group_city: {group_city}'.format(group_city=self.query.group_city))
            for i_key, i_value in enumerate(city_group):
                i_name = re.sub(r'\<.*?\>', "", i_value['caption'])
                i_value['long_name'] = i_name
            self.query.group_city = city_group
            self.user_keyboard(bot, from_user)
            return True
        else:
            self.query.status -= 1
            logger.info('города {name} не найдено: команда {comm}, status={status} пользователь id:{id}'.format(
                name=city, comm=self.command, status=self.query.status, id=from_user))
            bot.send_message(from_user, 'города {name} не найдено'.format(name=city))
            bot.send_message(from_user, 'Введите город, в котором будет проводиться поиск')
            return False

    def search_hotels(self, bot: TeleBot, from_user: int, sort_order: str) -> bool:
        """
        Метод поиска отелей в выбранном городе и сохранение результата в hotels
        :param bot: сам бот
        :param from_user: id пользователя
        :param sort_order: метод сортировки результатов
        :return: bool
        """
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = self.query.city
        logger.info('query.city: {city}'.format(city=self.query.city))
        checkIn_day = self.query.date_range['checkIn_day']
        checkOut_day = self.query.date_range['checkOut_day']
        action = 'load'
        lang_user, currency, currency_str = self.query.action_locale(self, action)
        querystring = {"destinationId": current_city['destinationId'], "pageNumber": "1",
                       "pageSize": self.query.number_hotels, "checkIn": checkIn_day,
                       "checkOut": checkOut_day, "adults1": "1", "sortOrder": sort_order, "locale": lang_user,
                       "currency": currency
                       }
        try:
            response = requests.request("GET", rapidapi_connect['url_hotels'], headers=rapidapi_connect['headers'],
                                        params=querystring, timeout=30)
            if response.status_code == 200:
                data = json.loads(response.text)
                self.query.hotels = data['data']['body']['searchResults']['results']

                if len(self.query.hotels) > 0:
                    logger.info('Hotels: {hotels}'.format(hotels=self.query.hotels))
                    for num, hotel in enumerate(self.query.hotels, 1):
                        i_hotel = self.hotel_information(hotel, num, currency_str)
                        bot.send_message(from_user, i_hotel)
                        if self.query.number_photo:
                            self.search_hotel_photo(bot, from_user, hotel['id'])
                else:
                    bot.send_message(from_user, 'Отелей в указанном городе не найдено')
                self.end_query(bot, from_user)
                return True
            else:
                logger.info('response.status_code != 200. Сервер не отвечает. Отели не найдены.')
                end_message = 'Сервер не отвечает. Отели не найдены.'
                self.query.status -= 1
                self.end_query(bot, from_user, end_message)
                return False
        except ReadTimeout:
            end_message = 'Время ожидания ответа сервера истекло. Отели не найдены.'
            logger.info('{end_message} Команда {comm}, пользователь id:{id}'.format(
                end_message=end_message, comm=self.command, id=from_user))
            self.query.status -= 1
            self.end_query(bot, from_user, end_message)
            return False

    def search_best_hotels(self, bot: TeleBot, from_user: int, sort_order: str) -> bool:
        """
        Метод поиска отелей в выбранном городе для команды /bestdeal и сохранение результата в hotels
        :param bot: сам бот
        :param from_user: id пользователя
        :param sort_order: метод сортировки результатов
        :return: bool
        """
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = self.query.city
        checkIn_day = self.query.date_range['checkIn_day']
        checkOut_day = self.query.date_range['checkOut_day']
        action = 'load'
        lang_user, currency, currency_str = self.query.action_locale(self.query, action)
        self.query.hotels = []
        pageNumber = 1
        find_number = 0
        price_min = self.query.price['min']
        price_max = self.query.price['max']
        check_delta_days = self.query.date_range['delta_days']
        if currency == 'RUB':
            price_min = price_min * check_delta_days
            price_max = price_max * check_delta_days
        while len(self.query.hotels) < self.query.number_hotels:
            if pageNumber <= 10:
                bot.send_message(from_user, 'Подождите, идет поиск вариантов. выполняем запрос № ' + str(pageNumber))
                querystring = {"destinationId": current_city['destinationId'], "pageNumber": pageNumber,
                               "pageSize": "25",
                               "checkIn": checkIn_day, "checkOut": checkOut_day, "adults1": "1",
                               "priceMin": price_min,
                               "priceMax": price_max,
                               "sortOrder": sort_order, "locale": lang_user, "currency": currency}
                logger.info('Поиск отелей /bestdeal querystring={querystring}'.format(querystring=querystring))
                try:
                    response = requests.request("GET", rapidapi_connect['url_hotels'],
                                                headers=rapidapi_connect['headers'],
                                                params=querystring, timeout=30)
                    if response.status_code == 200:
                        data = json.loads(response.text)
                        if len(data['data']['body']['searchResults']['results']) > 0:

                            for num, hotel in enumerate(data['data']['body']['searchResults']['results'], 1):
                                if len(self.query.hotels) < self.query.number_hotels:
                                    if hotel.get('landmarks')[0].get('distance'):
                                        i_landmarks = float(
                                            re.sub(',', '.', hotel['landmarks'][0]['distance'].split(' ')[0]))
                                        if self.query.distance['min'] <= i_landmarks <= \
                                                self.query.distance['max']:
                                            self.query.hotels.append(hotel)
                                            find_number += 1
                                            i_hotel = self.hotel_information(hotel, find_number, currency_str)
                                            bot.send_message(from_user, i_hotel)
                                            if self.query.number_photo:
                                                self.search_hotel_photo(bot, from_user, hotel['id'])
                                else:
                                    break
                    else:
                        logger.info('response.status_code != 200. Сервер не отвечает. Отели для bestdeal не найдены.')
                        end_message = 'Сервер не отвечает. Отели для bestdeal не найдены'
                        self.query.status -= 1
                        self.end_query(bot, from_user, end_message)
                        return False
                except ReadTimeout:
                    end_message = 'Время ожидания ответа сервера истекло. Отели для bestdeal не найдены.'
                    logger.info('{end_message} Команда {comm}, пользователь id:{id}'.format(
                        end_message=end_message, comm=self.command, id=from_user))
                    self.query.status -= 1
                    self.end_query(bot, from_user, end_message)
                    return False
                pageNumber += 1
            else:
                bot.send_message(from_user, 'Просмотрено более 250 вариантов, поиск прекращен')
                break
        if len(self.query.hotels) == 0:
            bot.send_message(from_user, 'Отелей в указанном городе не найдено')
        self.end_query(bot, from_user)
        return True

    def search_hotel_photo(self, bot: TeleBot, from_user: int, id_hotel: str) -> bool:
        """
        Метод поиска фотографий в выбранном отеле и сохранение результата в photos
        :param bot: сам бот
        :param from_user: id пользователя
        :param id_hotel: id отеля
        :return: bool
        """
        querystring = {"id": id_hotel}
        try:
            response = requests.request("GET", rapidapi_connect['url_photo'], headers=rapidapi_connect['headers'],
                                        params=querystring, timeout=30)
            if response.status_code == 200:
                data = json.loads(response.text)
                self.query.photos = data.get('hotelImages')
                media_group = list()
                if len(self.query.photos) > 0:
                    logger.info('query.photo: {photo}'.format(photo=self.query.photos))
                    for num, photo in enumerate(self.query.photos, 1):
                        if num <= self.query.number_photo:
                            media_group.append(types.InputMediaPhoto(media=re.sub('{size}', "z", photo.get('baseUrl'))))
                bot.send_media_group(from_user, media=media_group)
                return True
            else:
                logger.info('response.status_code != 200. Сервер не отвечает. Фото не найдены.')
                bot.send_message(from_user, 'Сервер не отвечает. Фото не найдены')
                self.query.status -= 1
                self.end_query(bot, from_user)
                return False
        except ReadTimeout:
            end_message = 'Время ожидания ответа сервера истекло.Фото не найдены.'
            logger.info('{end_message} Команда {comm}, пользователь id:{id}'.format(
                end_message=end_message, comm=self.command, id=from_user))
            self.query.status -= 1
            self.end_query(bot, from_user, end_message)
            return False

    def hotel_information(self, hotel: Dict[str, Any], find_number: int, currency_str: str) -> str:
        """
        Метод сбора данных об отеле для вывода пользователю
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
        i_date = self.query.date_range['checkIn_day'].split('-')
        checkIn_day = '{d}.{m}.{Y}'.format(d=i_date[2], m=i_date[1], Y=i_date[0])
        i_date = self.query.date_range['checkOut_day'].split('-')
        checkOut_day = '{d}.{m}.{Y}'.format(d=i_date[2], m=i_date[1], Y=i_date[0])
        check_delta_days = self.query.date_range['delta_days']
        str_days = 'сутки'
        if check_delta_days % 10 != 1:
            str_days = 'суток'
        price_day = hotel['ratePlan']['price']['exactCurrent']
        price_all = price_day
        if currency_str == 'USD':
            price_all = round(price_all * check_delta_days, 2)
        else:
            price_day = round(price_day / check_delta_days, 2)
        str_price_day = 'Стоимость проживания за сутки: {price_day} {currency_str}'.format(price_day=price_day,
                                                                                           currency_str=currency_str)
        str_price_all = 'Стоимость проживания за {check_delta_days} {str_days} с {checkIn_day} по {checkOut_day}: ' \
                        '{price_all} {currency_str}'.format(check_delta_days=check_delta_days,
                                                            str_days=str_days,
                                                            checkIn_day=checkIn_day,
                                                            checkOut_day=checkOut_day, price_all=price_all,
                                                            currency_str=currency_str)
        landmarks = 'Расстояние от центра города - {r}'.format(r=hotel['landmarks'][0]['distance'])
        site = 'https://ru.hotels.com/ho' + str(hotel['id'])
        hotel_info = '{num}. {name}.\nРейтинг отеля:{rating}\nАдрес: {address}.\n' \
                     '{str_price_day}\n{str_price_all}\nРасстояние - {landmarks}\nСайт: {hotel_site}\n'.format(
                        num=find_number, name=hotel['name'],
                        rating='\U00002B50' * int(hotel['starRating']),
                        address=address,
                        str_price_day=str_price_day, str_price_all=str_price_all,
                        currency_str=currency_str, landmarks=landmarks,
                        hotel_site=site)
        return hotel_info

    def end_query(self, bot: TeleBot, from_user: int, end_message='Запрос выполнен, введите другую команду ') -> None:
        """
        Метод завершения запроса и сохранения его в истории
        :param bot: сам бот
        :param from_user: id пользователя
        :param end_message: сообщение для пользователя
        :return: None
        """
        bot.send_message(from_user, end_message)
        if self.query.status != 0:
            current_day: datetime = datetime.datetime.utcnow()
            check_day: str = current_day.strftime('%d-%m-%Y %H:%M:%S')
            self.history[check_day] = [self.command, self.query]
            with db:
                History_db.create(key=from_user,
                                  value=[check_day, self.command, self.query.query_json()])
            logger.info('Выполненный запрос пользователя id:{id} сохранен в базу'.format(id=from_user))
        else:
            logger.info(
                'Выполненный запрос пользователя id:{id} не содержит данных и не сохранен в базу'.format(id=from_user))
        self.command = ""
        bot.send_message(from_user,
                         'Команды бота:\n'
                         '/lowprice — вывод самых дешёвых отелей в городе\n'
                         '/highprice — вывод самых дорогих отелей в городе\n'
                         '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                         '/history - история поиска\n')

    def user_keyboard(self, bot: TeleBot, from_user: int) -> None:
        """
        Метод вывода клавиатуры с возможными вариантами найденных городов
        :param bot: сам бот
        :param from_user: id пользователя
        :return: None
        """
        keyboard = types.InlineKeyboardMarkup()
        for i_key, i_value in enumerate(self.query.group_city):
            keyboard.add(
                types.InlineKeyboardButton(text=i_value['long_name'], callback_data='city_' + i_value['destinationId']))
        keyboard.add(types.InlineKeyboardButton(text='Города нет в списке, повторить ввод',
                                                callback_data='city_' + 'repeat'))
        question = 'Выберите город из списка'
        bot.send_message(from_user, text=question, reply_markup=keyboard)
