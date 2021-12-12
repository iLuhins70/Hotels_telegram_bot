import datetime
from telebot import types, TeleBot
from telebot.types import Message
from history import user_list
from loader import logger
from telegramcalendar import create_calendar


@logger.catch
def search(bot: TeleBot, message: Message, user_list: dict, from_user: int) -> None:
    """
    Основная функция перераспределения запроса в зависимости от ответа пользователя и статуса запроса
    user_list[from_user].query.status:
    0 - начало поиска, ждем ввода города
    1 - введен город для поиска, ищем и выводим список найденных городов (вывод кнопок)
    2 - выбран город из списка, спросим min стоимость, если /bestdeal  или дату заезда (к статусу 8)

    3 - /bestdeal если стоимость введена правильно, спросим max стоимость
    4 - /bestdeal если стоимость введена правильно, переходим в вопросам о расстоянии от центра
    5 - /bestdeal спросим min расстояние от центра
    6 - /bestdeal если расстояние введено правильно, спросим max расстояние от центра
    7 - /bestdeal если расстояние введено правильно, спросим дату заезда

    8 - если дата введено правильно, спросим дату отъезда
    9 - если дата введено правильно, спросим дату отъезда
   10 - введено правильная дата отъезда, спросим количество отелей
   11 - введено количество отелей, необходимо проверить ввод
   12 - введено правильное количество отелей, спросим про необходимость вывода фотографий (вывод кнопок)
   13 - введен ответ о необходимости фотографий, решаем, спрашивать ли об их количестве, если нет то к статусу 15
   14 - введено количество фотографий, необходимо проверить ввод
   15 - введено правильное количество фотографий, исполняем запрос

    :param bot: сам бот
    :param message: сообщение пользователя
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    current_command = user_list[from_user].command
    if user_list[from_user].query.status == 0:
        user_list[from_user].query.status += 1
        bot.send_message(from_user, 'Введите город, в котором будет проводиться поиск')
    elif user_list[from_user].query.status == 1:
        user_list[from_user].query.status += 1
        name_city(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 2:
        if current_command == '/bestdeal':
            delta_price(message, bot, user_list, from_user)
        else:
            user_list[from_user].query.status += 6
            date_range(bot, user_list, from_user)
    elif 3 <= user_list[from_user].query.status <= 4:
        delta_price(message, bot, user_list, from_user)
    elif 5 <= user_list[from_user].query.status <= 7:
        delta_distance(message, bot, user_list, from_user)
    elif 8 <= user_list[from_user].query.status <= 10:
        date_range(bot, user_list, from_user)
    elif user_list[from_user].query.status == 11:
        number_hotels(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 12:
        user_list[from_user].query.status += 1
        photo_question(bot, from_user)
    elif user_list[from_user].query.status == 13:
        user_list[from_user].query.status += 1
        if user_list[from_user].query.number_photo is None:
            user_list[from_user].query.status = 15
            search_hotel(bot, user_list, from_user)
        else:
            bot.send_message(from_user,
                             'Введите количество фотографий, которые необходимо вывести в результате (не больше 10)')
    elif user_list[from_user].query.status == 14:
        number_photo(message, bot, user_list, from_user)
    elif user_list[from_user].query.status == 15:
        search_hotel(bot, user_list, from_user)


@logger.catch
def name_city(message: Message, bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция запуска поиска города, вызывает метод класса запроса
    :param message: сообщение пользователя
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    user_list[from_user].search_cities(message, bot, from_user)


@logger.catch
def delta_price(message: Message, bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция ввода значений минимальной и максимальной стоимости проживания и проверка их на корректность
    :param message: сообщение пользователя
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    currency_str = user_list[from_user].query.locale['currency_str']
    if user_list[from_user].query.status == 2:
        user_list[from_user].query.status += 1
        bot.send_message(from_user,
                         'Введите минимальную стоимость проживания в сутки, {currency_str}'.format(
                             currency_str=currency_str))
    elif user_list[from_user].query.status == 3:
        try:
            if not user_list[from_user].query.price.get('min'):
                price = int(message.text)
                user_list[from_user].query.price['min'] = price
            user_list[from_user].query.status += 1
            bot.send_message(from_user, 'Введите максимальную стоимость проживания в сутки, {currency_str}'.format(
                currency_str=currency_str))
        except ValueError:
            bot.send_message(from_user, 'введите количество цифрами')
    elif user_list[from_user].query.status == 4:
        try:
            if not user_list[from_user].query.price.get('max'):
                price = int(message.text)
                user_list[from_user].query.price['max'] = price
            user_list[from_user].query.status += 1
            if user_list[from_user].query.price['min'] > user_list[from_user].query.price['max']:
                user_list[from_user].query.price['min'], user_list[from_user].query.price['max'] = \
                    user_list[from_user].query.price['max'], user_list[from_user].query.price['min']
            bot.send_message(from_user,
                             'диапазон цен от {min_price} {currency_str}  до {max_price} {currency_str}'.format(
                                 min_price=user_list[from_user].query.price['min'],
                                 max_price=user_list[from_user].query.price['max'],
                                 currency_str=currency_str))
            search(bot, message, user_list, from_user)
        except ValueError:
            bot.send_message(from_user, 'введите количество цифрами')


@logger.catch
def delta_distance(message: Message, bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция ввода значений минимального и максимального расстояния от центра города и проверка их на корректность
    :param message: сообщение пользователя
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    distance = user_list[from_user].query.locale['distance']
    if user_list[from_user].query.status == 5:
        user_list[from_user].query.status += 1
        bot.send_message(from_user,
                         'Введите минимальное расстояние от центра, {distance}'.format(distance=distance))
    elif user_list[from_user].query.status == 6:
        try:
            if not user_list[from_user].query.distance.get('min'):
                input_distance = float(message.text)
                user_list[from_user].query.distance['min'] = input_distance
            user_list[from_user].query.status += 1
            bot.send_message(from_user,
                             'Введите максимальное расстояние от центра, {distance}'.format(distance=distance))
        except ValueError:
            bot.send_message(from_user, 'Неправильный ввод, повторите')
    elif user_list[from_user].query.status == 7:
        try:
            if not user_list[from_user].query.distance.get('max'):
                input_distance = float(message.text)
                user_list[from_user].query.distance['max'] = input_distance
            user_list[from_user].query.status += 1
            if user_list[from_user].query.distance['min'] > user_list[from_user].query.distance['max']:
                user_list[from_user].query.distance['min'], user_list[from_user].query.distance['max'] = \
                    user_list[from_user].query.distance['max'], user_list[from_user].query.distance['min']
            bot.send_message(from_user,
                             'Расстояние от центра: {min_distance} {distance}  до {max_distance} {distance}'.format(
                                 min_distance=user_list[from_user].query.distance['min'],
                                 max_distance=user_list[from_user].query.distance['max'],
                                 distance=distance))
            search(bot, message, user_list, from_user)
        except ValueError:
            bot.send_message(from_user, 'введите количество цифрами')
            bot.register_next_step_handler(message, delta_distance, bot, user_list, from_user)


@logger.catch
def date_range(bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция ввода даты заезда и выезда и вычисление общего количества суток для проживания
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    logger.info('data_range. status={status}'.format(status=user_list[from_user].query.status))
    if user_list[from_user].query.status == 10:
        user_list[from_user].query.status += 1
        temp_date = user_list[from_user].query.date_range['checkIn_day'].split('-')
        new_date_1 = datetime.date(int(temp_date[0]), int(temp_date[1]), int(temp_date[2]))
        temp_date = user_list[from_user].query.date_range['checkOut_day'].split('-')
        new_date_2 = datetime.date(int(temp_date[0]), int(temp_date[1]), int(temp_date[2]))
        if new_date_2 == new_date_1:
            bot.send_message(from_user,
                             'Введены одинаковые даты. Будет рассчитана стоимость проживания за 1 сутки')
            new_date_2 += datetime.timedelta(days=1)
        elif new_date_2 < new_date_1:
            user_list[from_user].query.date_range['checkIn_day'], user_list[from_user].query.date_range[
                'checkOut_day'] = user_list[from_user].query.date_range['checkOut_day'], \
                                  user_list[from_user].query.date_range['checkIn_day']
        user_list[from_user].query.date_range['delta_days'] = abs((new_date_2 - new_date_1).days)
        bot.send_message(from_user, 'Введите количество отелей, которые необходимо вывести в результате (не больше 25)')
    else:
        question = 'Выберите дату заезда'
        if not user_list[from_user].query.date_range.get('now_day'):

            user_list[from_user].query.date_range['now_day'] = datetime.datetime.utcnow().strftime('%Y-%m-%d')

        if user_list[from_user].query.date_range.get('checkIn_day') and not user_list[from_user].query.date_range.get(
                'checkOut_day'):
            question = 'Выберите дату отъезда'
            temp_date = user_list[from_user].query.date_range['checkIn_day'].split('-')
            user_list[from_user].query.date_range['now_day'] = user_list[from_user].query.date_range['checkIn_day']
        else:
            temp_date = user_list[from_user].query.date_range['now_day'].split('-')
        new_date = datetime.date(int(temp_date[0]), int(temp_date[1]), int(temp_date[2]))
        markup = create_calendar(new_date.year, new_date.month)
        bot.send_message(from_user, question, reply_markup=markup)


@logger.catch
def number_hotels(message: Message, bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция ввода количества отелей для поиска и проверка его на корректность
    :param message: сообщение пользователя
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    if message.text.isdigit():
        if 0 < int(message.text) < 26:
            number = int(message.text)
            city = user_list[from_user].query.city
            user_list[from_user].query.number_hotels = number
            bot.send_message(from_user,
                             'Количество отелей для поиска в городе {0}: {1}'.format(city['long_name'], message.text))
            user_list[from_user].query.status += 1
            search(bot, message, user_list, from_user)
        else:
            bot.send_message(from_user, 'число вне диапазона, повторите ввод')
    else:
        bot.send_message(from_user, 'введите количество цифрами')


@logger.catch
def photo_question(bot: TeleBot, from_user: int) -> None:
    """
    Функция вывода клавиатуры для запроса необходимости поиска фотографий
    :param bot: сам бот
    :param from_user: id пользователя
    :return: None
    """
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Да', callback_data='Yes photo'),
                 types.InlineKeyboardButton(text='Нет', callback_data='No photo'))
    question = 'Выводить фотографии для каждого отеля?'
    bot.send_message(from_user, text=question, reply_markup=keyboard)


@logger.catch
def number_photo(message: Message, bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция ввода количества фотографий и проверка его на корректность
    :param message: сообщение пользователя
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    if message.text.isdigit():
        if 0 < int(message.text) < 11:
            number = int(message.text)
            user_list[from_user].query.number_photo = number
            bot.send_message(from_user,
                             'Количество фотографий для поиска: {0}'.format(message.text))
            user_list[from_user].query.status += 1
            search(bot, message, user_list, from_user)
        else:
            bot.send_message(from_user, 'число вне диапазона, повторите ввод')
    else:
        bot.send_message(from_user, 'введите количество цифрами')


@logger.catch
def search_hotel(bot: TeleBot, user_list: user_list, from_user: int) -> None:
    """
    Функция запуска необходимого запроса из методов класса запрос
    :param bot: сам бот
    :param user_list: список пользователей
    :param from_user: id пользователя
    :return: None
    """
    sortOrder = "PRICE"
    if user_list[from_user].command == '/highprice':
        sortOrder = "PRICE_HIGHEST_FIRST"
        user_list[from_user].search_hotels(bot,from_user, sortOrder)
    elif user_list[from_user].command == '/lowprice':
        user_list[from_user].search_hotels(bot, from_user, sortOrder)
    elif user_list[from_user].command == '/bestdeal':
        user_list[from_user].search_best_hotels(bot, from_user, sortOrder)
