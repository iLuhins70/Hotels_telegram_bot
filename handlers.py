from telebot import types


def search(bot, message, user_list, from_user):
    """
    user_list[from_user].query.status:
    0 - начало поиска, ждем ввода города
    1 - введен город для поиска, ишем и выводим список найденных городов (вывод кнопок)
    2 - выбран город из списка, спросим количество отелей
    3 - введено количество отелей, необходимо проверить ввод
    4 - введено правильное количество отелей, спросим про необходимость вывода фотографий (вывод кнопок)
    5 - введен ответ о необходимости фотографий, решаем, спрашивать ли об их количестве
    6 - введено количество фотографий, необходимо проверить ввод
    7 - введено правильное количество фотографий, исполняем запрос
    :param bot:
    :param message:
    :param user_list:
    :param from_user:
    :return:
    """
    current_command = user_list[from_user].command
    if user_list[from_user].query.status == 0:
        user_list[from_user].query.status = 1
        bot.send_message(from_user, 'Введите город, в котором будет проводиться поиск')
    elif user_list[from_user].query.status == 1:
        user_list[from_user].query.status = 2
        name_city(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 2:
        if current_command == '/bestdeal':
            if user_list[from_user].query.distance.get('max'):
                user_list[from_user].query.status = 3
                bot.send_message(from_user,
                                 'bestdeal Введите количество отелей, которые необходимо вывести в результате (не больше 25)')

            elif user_list[from_user].query.price.get('max'):
                delta_distance(message, bot, user_list, from_user)
            elif user_list[from_user].query.city:

                delta_price(message, bot, user_list, from_user)
        else:
            user_list[from_user].query.status = 3
            bot.send_message(from_user,
                             'Введите количество отелей, которые необходимо вывести в результате (не больше 25)')
    elif user_list[from_user].query.status == 3:

        number_city(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 4:
        user_list[from_user].query.status = 5
        photo_question(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 5:
        user_list[from_user].query.status = 6
        print('number_photo', user_list[from_user].query.number_photo)
        if user_list[from_user].query.number_photo is None:
            user_list[from_user].query.status = 7
            search_hotel(message, bot, user_list, from_user)
        else:
            bot.send_message(from_user,
                             'Введите количество фотографий, которые необходимо вывести в результате (не больше 10)')
    elif user_list[from_user].query.status == 6:
        number_photo(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 7:
        search_hotel(message, bot, user_list, from_user)


def name_city(message, bot, user_list, from_user):
    user_list[from_user].query.search_cities(message, bot, user_list, from_user)


def delta_price(message, bot, user_list, from_user):
    currency_str = user_list[from_user].query.locale['currency_str']
    if not user_list[from_user].query.price:
        user_list[from_user].query.price['min'] = 0
        bot.send_message(from_user,
                         'Введите минимальную стоимость проживания, {currency_str}'.format(
                             currency_str=currency_str))
    elif user_list[from_user].query.price['min'] == 0:
        if message.text.isdigit():
            price = float(message.text)
            user_list[from_user].query.price['min'] = price
            user_list[from_user].query.price['max'] = 0
            bot.send_message(from_user, 'Введите максимальную стоимость проживания, {currency_str}'.format(
                currency_str=currency_str))
        else:
            bot.send_message(from_user, 'введите количество цифрами')
    elif user_list[from_user].query.price['max'] == 0:
        if message.text.isdigit():
            price = float(message.text)
            user_list[from_user].query.price['max'] = price
            if user_list[from_user].query.price['min'] > user_list[from_user].query.price['max']:
                user_list[from_user].query.price['min'], user_list[from_user].query.price['max'] = \
                    user_list[from_user].query.price['max'], user_list[from_user].query.price['min']
            bot.send_message(from_user,
                             'диапазон цен от {min_price} {currency_str}  до {max_price} {currency_str}'.format(
                                 min_price=user_list[from_user].query.price['min'],
                                 max_price=user_list[from_user].query.price['max'],
                                 currency_str=currency_str))
            search(bot, message, user_list, from_user)
        else:
            bot.send_message(from_user, 'введите количество цифрами')


def delta_distance(message, bot, user_list, from_user):
    distance = user_list[from_user].query.locale['distance']
    if not user_list[from_user].query.distance:
        user_list[from_user].query.distance['min'] = 0
        bot.send_message(from_user,
                         'Введите минимальное расстояние от центра, {distance}'.format(distance=distance))
    elif user_list[from_user].query.distance['min'] == 0:
        if message.text.isdigit():
            input_distance = float(message.text)

            user_list[from_user].query.distance['min'] = input_distance
            user_list[from_user].query.distance['max'] = 0
            bot.send_message(from_user,
                             'Введите максимальное расстояние от центра, {distance}'.format(distance=distance))
        else:
            bot.send_message(from_user, 'введите количество цифрами')
    elif user_list[from_user].query.distance['max'] == 0:
        if message.text.isdigit():

            input_distance = float(message.text)
            user_list[from_user].query.distance['max'] = input_distance
            if user_list[from_user].query.distance['min'] > user_list[from_user].query.distance['max']:
                user_list[from_user].query.distance['min'], user_list[from_user].query.distance['max'] = \
                    user_list[from_user].query.distance['max'], user_list[from_user].query.distance['min']
            bot.send_message(from_user,
                             'Расстояние от центра: {min_distance} {distance}  до {max_distance} {distance}'.format(
                                 min_distance=user_list[from_user].query.distance['min'],
                                 max_distance=user_list[from_user].query.distance['max'],
                                 distance=distance))

            search(bot, message, user_list, from_user)
        else:
            bot.send_message(from_user, 'введите количество цифрами')
            bot.register_next_step_handler(message, delta_distance, bot, user_list, from_user)


def number_city(message, bot, user_list, from_user):
    if message.text.isdigit():
        if 0 < int(message.text) < 26:
            number = int(message.text)

            city = user_list[from_user].query.city
            user_list[from_user].query.number_hotels = number
            bot.send_message(from_user,
                             'Количество отелей для поиска в городе {0}: {1}'.format(city['long_name'], message.text))
            user_list[from_user].query.status = 4
            search(bot, message, user_list, from_user)
        else:
            bot.send_message(from_user, 'число вне диапазона, повторите ввод')
    else:
        bot.send_message(from_user, 'введите количество цифрами')


def photo_question(message, bot, user_list, from_user):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data='Yes photo'),
                 types.InlineKeyboardButton(text='Нет', callback_data='No photo'))
    question = 'Выводить фотографии для каждого отеля?'
    bot.send_message(from_user, text=question, reply_markup=keyboard)


def number_photo(message, bot, user_list, from_user):
    if message.text.isdigit():
        if 0 < int(message.text) < 11:
            number = int(message.text)

            user_list[from_user].query.number_photo = number
            bot.send_message(from_user,
                             'Количество фотографий для поиска: {0}'.format(message.text))
            user_list[from_user].query.status = 7
            search(bot, message, user_list, from_user)
        else:
            bot.send_message(from_user, 'число вне диапазона, повторите ввод')
    else:
        bot.send_message(from_user, 'введите количество цифрами')


def search_hotel(message, bot, user_list, from_user):
    sortOrder = "PRICE"
    if user_list[from_user].command == '/highprice':
        sortOrder = "PRICE_HIGHEST_FIRST"
        user_list[from_user].query.search_hotels(message, bot, user_list, from_user, sortOrder)
    elif user_list[from_user].command == '/lowprice':

        user_list[from_user].query.search_hotels(message, bot, user_list, from_user, sortOrder)
    elif user_list[from_user].command == '/bestdeal':
        user_list[from_user].query.search_best_hotels(message, bot, user_list, from_user, sortOrder)
