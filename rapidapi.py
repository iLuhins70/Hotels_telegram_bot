import json
from loader import rapidapi_connect
from telebot import types
import requests
import re
import datetime


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

    def search_cities(self, message, bot, user_list, from_user):
        city = message.text
        if not user_list[from_user].query.group_city:

            detect = re.sub(r'[\Wа-яА-ЯёЁ]+', "ru", city)
            if detect == 'ru':

                bot.send_message(from_user, 'Начат поиск города на русском языке. Подождите...')
                lang_user = 'ru_RU'
                user_list[from_user].query.locale['locale'] = lang_user
                user_list[from_user].query.locale['distance'] = 'км'
                user_list[from_user].query.locale['currency'] = 'RUB'
                user_list[from_user].query.locale['currency_str'] = 'руб.'
            else:
                bot.send_message(from_user, 'Начат поиск города. Подождите... ')
                lang_user = 'en_US'
                user_list[from_user].query.locale['locale'] = lang_user
                user_list[from_user].query.locale['distance'] = 'miles'
                user_list[from_user].query.locale['currency'] = 'USD'
                user_list[from_user].query.locale['currency_str'] = '$'

            querystring = {"query": city, "locale": lang_user}
            print(rapidapi_connect['url_city'])
            print(rapidapi_connect['headers'])
            print(querystring)
            response = requests.request("GET", rapidapi_connect['url_city'], headers=rapidapi_connect['headers'],
                                        params=querystring)

            data = json.loads(response.text)

            suggestions = list(filter(lambda i_city: i_city['group'] == 'CITY_GROUP', data['suggestions']))[0][
                'entities']

            city_group = list(filter(lambda i_name: i_name['type'] == 'CITY', suggestions))
        else:
            city_group = user_list[from_user].query.group_city
        if len(city_group) > 0:
            keyboard = types.InlineKeyboardMarkup()
            for i_key, i_value in enumerate(city_group):
                i_name = re.sub(r'\<.*?\>', "", i_value['caption'])
                i_value['long_name'] = i_name
                keyboard.add(types.InlineKeyboardButton(text=i_name, callback_data=i_value['destinationId']))
            keyboard.add(types.InlineKeyboardButton(text='Города нет в списке, повторить ввод',
                                                    callback_data='repeat_city'))
            user_list[from_user].query.group_city = city_group
            question = 'Выберите город из списка'
            bot.send_message(from_user, text=question, reply_markup=keyboard)
        else:
            bot.send_message(from_user, 'города {name} не найдено'.format(name=city))
            bot.send_message(from_user, 'Введите город, в котором будет проводиться поиск')

    def search_hotels(self, message, bot, user_list, from_user, sortOrder):
        bot.send_message(from_user, 'Поиск отелей. Подождите...')

        current_city = user_list[from_user].query.city
        current_day = datetime.datetime.utcnow()
        delta = datetime.timedelta(days=1)
        tomorrow_day = current_day + delta
        checkIn_day = current_day.strftime('%Y-%m-%d')
        checkOut_day = tomorrow_day.strftime('%Y-%m-%d')
        lang_user = user_list[from_user].query.locale['locale']
        currency = user_list[from_user].query.locale['currency']
        currency_str = user_list[from_user].query.locale['currency_str']

        querystring = {"destinationId": current_city['destinationId'], "pageNumber": "1",
                       "pageSize": user_list[from_user].query.number_hotels, "checkIn": checkIn_day,
                       "checkOut": checkOut_day, "adults1": "1", "sortOrder": sortOrder, "locale": lang_user,
                       "currency": currency
                       }

        response = requests.request("GET", rapidapi_connect['url_hotels'], headers=rapidapi_connect['headers'],
                                    params=querystring)
        data = json.loads(response.text)

        user_list[from_user].query.hotels = data['data']['body']['searchResults']['results']
        if len(user_list[from_user].query.hotels) > 0:
            for num, hotel in enumerate(user_list[from_user].query.hotels, 1):
                address_list = [x for x in
                                [hotel['address'].get('streetAddress', ''), hotel['address'].get('extendedAddress', ''),
                                 hotel['address'].get('locality', ''), hotel['address'].get('postalCode', ''),
                                 hotel['address'].get('region', '')] if x != '']
                address = ', '.join(address_list)
                landmarks = hotel['landmarks'][0]['distance'] + ' от центра города'
                site = 'https://ru.hotels.com/ho' + str(hotel['id'])
                bot.send_message(from_user,
                                 '{num}. {name}.  Рейтинг отеля:{rating} Адрес: {address}. Стоимость проживания: '
                                 '{price} {currency_str}. {landmarks}. Сайт: {hotel_site}\n'.
                                 format(num=num, name=hotel['name'], rating='\U00002B50' * int(hotel['starRating']),
                                        address=address,
                                        price=hotel['ratePlan']['price']['exactCurrent'],
                                        currency_str=currency_str, landmarks=landmarks,
                                        hotel_site=site))
                if user_list[from_user].query.number_photo:
                    self.search_hotel_photo(message, bot, user_list, from_user, hotel['id'])
        else:
            bot.send_message(from_user, 'Отелей в указанном городе не найдено')
        self.end_query(message, bot, user_list, from_user)

    def search_best_hotels(self, message, bot, user_list, from_user, sortOrder):
        bot.send_message(from_user, 'Поиск отелей. Подождите...')
        current_city = user_list[from_user].query.city
        current_day = datetime.datetime.utcnow()
        delta = datetime.timedelta(days=1)
        tomorrow_day = current_day + delta
        checkIn_day = current_day.strftime('%Y-%m-%d')
        checkOut_day = tomorrow_day.strftime('%Y-%m-%d')
        lang_user = user_list[from_user].query.locale['locale']
        currency = user_list[from_user].query.locale['currency']
        currency_str = user_list[from_user].query.locale['currency_str']

        user_list[from_user].query.hotels = []
        pageNumber = 1
        find_number = 0
        while len(user_list[from_user].query.hotels) < user_list[from_user].query.number_hotels:
            if pageNumber <= 10:
                bot.send_message(from_user, 'Подождите, идет поиск вариантов. выполняем запрос № ' + str(pageNumber))
                print('страница', pageNumber, 'Найдено отелей', len(user_list[from_user].query.hotels))
                querystring = {"destinationId": current_city['destinationId'], "pageNumber": pageNumber,
                               "pageSize": "25",
                               "checkIn": checkIn_day, "checkOut": checkOut_day, "adults1": "1",
                               "priceMin": user_list[from_user].query.price['min'],
                               "priceMax": user_list[from_user].query.price['max'],
                               "sortOrder": sortOrder, "locale": lang_user, "currency": currency}
                response = requests.request("GET", rapidapi_connect['url_hotels'], headers=rapidapi_connect['headers'],
                                            params=querystring)
                data = json.loads(response.text)
                if len(data['data']['body']['searchResults']['results']) > 0:
                    print('результат > 0')
                    for num, hotel in enumerate(data['data']['body']['searchResults']['results'], 1):
                        if len(user_list[from_user].query.hotels) < user_list[from_user].query.number_hotels:
                            if hotel.get('landmarks')[0].get('distance'):
                                i_landmarks = float(re.sub(',', '.', hotel['landmarks'][0]['distance'].split(' ')[0]))
                                print(str(num), 'i_landmarks =', i_landmarks)
                                if user_list[from_user].query.distance['min'] <= i_landmarks <= \
                                        user_list[from_user].query.distance['max']:
                                    user_list[from_user].query.hotels.append(hotel)
                                    find_number += 1
                                    print(str(user_list[from_user].query.distance['min']), ' <=', str(i_landmarks),
                                          ' <=', str(user_list[from_user].query.distance['max']))
                                    print('+1, find_number =', find_number)
                                    address_list = [x for x in
                                                    [hotel['address'].get('streetAddress', ''),
                                                     hotel['address'].get('extendedAddress', ''),
                                                     hotel['address'].get('locality', ''),
                                                     hotel['address'].get('postalCode', ''),
                                                     hotel['address'].get('region', '')] if x != '']
                                    address = ', '.join(address_list)

                                    landmarks = hotel['landmarks'][0]['distance'] + ' от центра города'
                                    site = 'https://ru.hotels.com/ho' + str(hotel['id'])
                                    bot.send_message(from_user,
                                                     '{num}. {name}.  Рейтинг отеля:{rating} Адрес: {address}. Стоимость проживания: '
                                                     '{price} {currency_str}. {landmarks}. Сайт: {hotel_site}\n'.
                                                     format(num=find_number, name=hotel['name'],
                                                            rating='\U00002B50' * int(hotel['starRating']),
                                                            address=address,
                                                            price=hotel['ratePlan']['price']['exactCurrent'],
                                                            currency_str=currency_str, landmarks=landmarks,
                                                            hotel_site=site))
                                    if user_list[from_user].query.number_photo:
                                        self.search_hotel_photo(message, bot, user_list, from_user, hotel['id'])

                        else:
                            break
                pageNumber += 1

            else:
                bot.send_message(from_user, 'Просмотрено более 250 вариантов, поиск прекращен')
                break

        if len(user_list[from_user].query.hotels) == 0:
            bot.send_message(from_user, 'Отелей в указанном городе не найдено')
        self.end_query(message, bot, user_list, from_user)

    def search_hotel_photo(self, message, bot, user_list, from_user, id_hotel):

        querystring = {"id": id_hotel}

        response = requests.request("GET", rapidapi_connect['url_photo'], headers=rapidapi_connect['headers'],
                                    params=querystring)
        data = json.loads(response.text)

        user_list[from_user].query.photos = data.get('hotelImages')
        media_group = list()
        if len(user_list[from_user].query.photos) > 0:

            for num, photo in enumerate(user_list[from_user].query.photos, 1):
                if num <= user_list[from_user].query.number_photo:
                    media_group.append(types.InputMediaPhoto(media=re.sub('{size}', "z", photo.get('baseUrl'))))
        bot.send_media_group(from_user, media=media_group)

    def end_query(self, message, bot, user_list, from_user):
        bot.send_message(from_user, 'Запрос выполнен, введите другую команду ')
        current_day = datetime.datetime.utcnow()

        check_day = current_day.strftime('%d-%m-%Y %H:%M:%S')
        print(check_day)
        user_list[from_user].history[check_day] = [user_list[from_user].command, user_list[from_user].query]
        user_list[from_user].command = ""
        bot.send_message(from_user,
                         'Команды бота:\n'
                         '/lowprice — вывод самых дешёвых отелей в городе\n'
                         '/highprice — вывод самых дорогих отелей в городе\n'
                         '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                         '/history - история поиска\n')
