import json
from loader import rapidapi_connect
from loader import logger
from telebot import types
import requests
import re
import datetime


@logger.catch
class API_request:

    def __init__(self):
        self.status = 0
        self.group_city = None
        self.city = ''
        self.destination_id = ''
        self.number_hotels = 0
        self.price = dict()
        self.distance = dict()
        self.hotels = None
        self.number_photo = None
        self.photos = None
        self.locale = dict()

    def action_locale(self, action, lang_user='en_US', distance='miles', currency='USD', currency_str='$'):
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

    @staticmethod
    def check_day():
        current_day = datetime.datetime.utcnow()
        delta = datetime.timedelta(days=1)
        tomorrow_day = current_day + delta
        checkIn_day = current_day.strftime('%Y-%m-%d')
        checkOut_day = tomorrow_day.strftime('%Y-%m-%d')
        return checkIn_day, checkOut_day

    def search_cities(self, message, bot, user_list, from_user):
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
                self.status -= 1
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
            logger.info('города {name} не найдено: команда {comm}, пользователь id:{id}'.format(name=city,
                                                                                                comm=user_list[
                                                                                                    from_user].command,
                                                                                                id=from_user))
            bot.send_message(from_user, 'города {name} не найдено'.format(name=city))
            bot.send_message(from_user, 'Введите город, в котором будет проводиться поиск')

    def search_hotels(self, message, bot, user_list, from_user, sort_order):
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = self.city
        checkIn_day, checkOut_day = self.check_day()
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
                    i_hotel = self.hotel_information(hotel, num, currency_str)
                    bot.send_message(from_user, i_hotel)
                    if self.number_photo:
                        self.search_hotel_photo(message, bot, user_list, from_user, hotel['id'])
            else:
                bot.send_message(from_user, 'Отелей в указанном городе не найдено')
            self.end_query(bot, user_list, from_user)
        else:
            logger.info('response.status_code != 200. Сервер не отвечает. Отели не найдены.')
            bot.send_message(from_user, 'Сервер не отвечает. Отели не найдены.')
            self.status -= 1
            self.end_query(bot, user_list, from_user)

    def search_best_hotels(self, message, bot, user_list, from_user, sort_order):
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = self.city
        checkIn_day, checkOut_day = self.check_day()
        action = 'load'
        lang_user, currency, currency_str = self.action_locale(self, action)
        self.hotels = []
        pageNumber = 1
        find_number = 0
        while len(self.hotels) < self.number_hotels:
            if pageNumber <= 10:
                bot.send_message(from_user, 'Подождите, идет поиск вариантов. выполняем запрос № ' + str(pageNumber))
                querystring = {"destinationId": current_city['destinationId'], "pageNumber": pageNumber,
                               "pageSize": "25",
                               "checkIn": checkIn_day, "checkOut": checkOut_day, "adults1": "1",
                               "priceMin": self.price['min'],
                               "priceMax": self.price['max'],
                               "sortOrder": sort_order, "locale": lang_user, "currency": currency}
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
                                        i_hotel = self.hotel_information(hotel, find_number, currency_str)
                                        bot.send_message(from_user, i_hotel)
                                        if self.number_photo:
                                            self.search_hotel_photo(message, bot, user_list, from_user, hotel['id'])
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

    def search_hotel_photo(self, message, bot, user_list, from_user, id_hotel):
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
    def hotel_information(hotel, find_number, currency_str):
        address_list = [x for x in
                        [hotel['address'].get('streetAddress', ''),
                         hotel['address'].get('extendedAddress', ''),
                         hotel['address'].get('locality', ''),
                         hotel['address'].get('postalCode', ''),
                         hotel['address'].get('region', '')] if x != '']
        address = ', '.join(address_list)

        landmarks = hotel['landmarks'][0]['distance'] + ' от центра города'
        site = 'https://ru.hotels.com/ho' + str(hotel['id'])
        hotel_info = '{num}. {name}.  Рейтинг отеля:{rating} Адрес: {address}. ' \
                     'Стоимость проживания: {price} {currency_str}. {landmarks}. Сайт: {hotel_site}\n'.format(
                        num=find_number, name=hotel['name'],
                        rating='\U00002B50' * int(hotel['starRating']),
                        address=address,
                        price=hotel['ratePlan']['price']['exactCurrent'],
                        currency_str=currency_str, landmarks=landmarks,
                        hotel_site=site)
        return hotel_info

    def end_query(self, bot, user_list, from_user):
        bot.send_message(from_user, 'Запрос выполнен, введите другую команду ')
        current_day = datetime.datetime.utcnow()

        check_day = current_day.strftime('%d-%m-%Y %H:%M:%S')
        user_list[from_user].history[check_day] = [user_list[from_user].command, self]
        user_list[from_user].command = ""
        bot.send_message(from_user,
                         'Команды бота:\n'
                         '/lowprice — вывод самых дешёвых отелей в городе\n'
                         '/highprice — вывод самых дорогих отелей в городе\n'
                         '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                         '/history - история поиска\n')


@logger.catch
def user_keyboard(bot, user_list, from_user):
    keyboard = types.InlineKeyboardMarkup()
    for i_key, i_value in enumerate(user_list[from_user].query.group_city):
        keyboard.add(types.InlineKeyboardButton(text=i_value['long_name'], callback_data=i_value['destinationId']))
    keyboard.add(types.InlineKeyboardButton(text='Города нет в списке, повторить ввод',
                                            callback_data='repeat_city'))
    question = 'Выберите город из списка'
    bot.send_message(from_user, text=question, reply_markup=keyboard)
