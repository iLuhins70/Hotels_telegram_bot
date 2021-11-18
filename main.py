import datetime
from typing import List, Dict, Optional

import telebot
from telebot import types, apihelper

from loader import bot
from loader import logger
from rapidapi import API_request
from handlers import search
from history import open_history, load_history, del_history
from telegramcalendar import create_calendar
import calendar


class User:
    """
    класс Пользователь. Хранит текущий запрос, а также историю запросов
    :param
    """

    def __init__(self) -> None:
        self.command: str = ''
        self.query: API_request = API_request()
        self.history: Dict[str, List[str, API_request]] = dict()


user_list: Dict[int, User] = dict()
logger.info('Запуск бота.')


@bot.message_handler(commands=['start'])
@logger.catch
def start_message(message: telebot.types.Message) -> None:
    """
    Функция запуска бота Телеграмм. Выполняется при вводе пользователем команды /start
    :param message: сообщение от бота
    :return: None
    """
    from_user: int = message.from_user.id
    if from_user not in user_list:
        user_list[from_user] = User()
        bot.send_message(from_user, 'Здравствуйте, я Ваш помощник!\nЯ помогу Вам найти отель для поездки')
        logger.info('Новый пользователь id:{id}'.format(id=from_user))
        temp_query = API_request()
        res = load_history(user_list, from_user, temp_query)
    else:
        bot.send_message(from_user, 'И снова здравствуйте!')
    help_message(message)


@bot.message_handler(commands=['help'])
@logger.catch
def help_message(message: telebot.types.Message) -> None:
    """
    Функция вывода краткой справки по боту. Выполняется при вводе пользователем команды /help
    :param message: сообщение от бота
    :return: None
    """
    bot.send_message(message.chat.id,
                     'Команды бота:\n'
                     '/start - запуск бота\n'
                     '/lowprice — вывод самых дешёвых отелей в городе\n'
                     '/highprice — вывод самых дорогих отелей в городе\n'
                     '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                     '/history - история поиска\n')


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
@logger.catch
def search_price(message: telebot.types.Message, from_user: Optional[int] = None) -> None:
    """
    Функция запуска поиска отелей. Выполняется при вводе пользователем команд из списка
    :param message: сообщение от бота
    :param from_user: id текущего пользователя
    :return: None
    """
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        try:
            bot.edit_message_reply_markup(from_user, message_id=message.id - 1, reply_markup=None)
        except apihelper.ApiTelegramException:
            logger.info('попытка убрать клавиатуру в команде bestdeal во время доп. запросов')
        if user_list[from_user].command == '':
            user_list[from_user].query = API_request()
            user_list[from_user].command = message.text
            user_list[from_user].query.status = 0
            logger.info('Новый запрос {comm} пользователя id:{id}'.format(comm=message.text, id=from_user))
            search(bot, message, user_list, from_user)
        else:
            logger.info('Новый запрос на смену команды на {comm} пользователя id:{id}'.format(
                comm=message.text, id=from_user))
            change_commands_question(message, bot, user_list, from_user)


@bot.message_handler(commands=['history'])
@logger.catch
def history(message: telebot.types.Message, from_user: Optional[int] = None) -> None:
    """
    Функция вывода истории поиска. Выполняется при вводе пользователем команды /history
    :param message: сообщение от бота
    :param from_user: id текущего пользователя
    :return: None
    """
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        if user_list[from_user].command == '':
            logger.info('История пользователя id:{id}'.format(id=from_user))
            open_history(bot, user_list, from_user)
        else:
            logger.info(
                'Новый запрос на смену команды на {comm} пользователя id:{id}'.format(comm=message.text, id=from_user))
            change_commands_question(message, bot, user_list, from_user)


@bot.message_handler(content_types=['text'])
@logger.catch
def text_input(message: telebot.types.Message, from_user: Optional[int] = None) -> None:
    """
    Функция ожидает ввод от пользователя и продолжает поиск.
    :param message: сообщение от бота
    :param from_user: id текущего пользователя
    :return: None
    """
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        if user_list[from_user].command == '':
            help_message(message)
        else:
            logger.info('Продолжим поиск.Пользователь id:{id}'.format(id=from_user))
            search(bot, message, user_list, from_user)


@bot.callback_query_handler(func=lambda call: True)
@logger.catch
def callback_worker(call: telebot.types.CallbackQuery) -> None:
    """
    Функция ожидает нажатие на кнопку от пользователя и перенаправляет в функцию в зависимости от того, что спрашиваем:
     - startswith('/'): выбрана команда для продолжения поиска или начала нового поиска
     - endswith('photo'): запрос о необходимости вывода фотографий
     - startswith('history_'): запуск поиска из сохраненной истории
     - startswith('city_'): выбор города из списка
     - остальное: выбор даты из календаря
    :param call: callback от бота
    :return: None
    """
    from_user: int = call.from_user.id
    if from_user in user_list:
        bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="OK!")
        if call.data.startswith('/'):
            change_command(call, bot, user_list, from_user)
        elif call.data.endswith('photo'):
            question_photo(call, bot, user_list, from_user)
        elif call.data.startswith('history_'):
            view_history(call, bot, user_list, from_user)
        elif call.data.startswith('city_'):
            selection_city(call, bot, user_list, from_user)
        else:
            logger.info('Вывод календаря')
            calendar_input_data(call, bot, user_list, from_user)
    else:
        bot.send_message(from_user, 'Бот был перезапущен, начните сеанс заново /start')


@logger.catch()
def change_command(call: telebot.types.CallbackQuery, bot: telebot.TeleBot, user_list: Dict[int, User],
                   from_user: int) -> None:
    """
    Функция в зависимости от выбора пользователя продолжает текущий поиск, либо запускает новый.
    При том текущий поиск сохраняется в истории пользователя
    :param call: callback от бота
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    message = bot.edit_message_reply_markup(from_user, message_id=call.message.message_id,
                                            reply_markup=None)
    message.text = call.data.split(' ')[0]
    if user_list[from_user].command != '/bestdeal' and user_list[from_user].query.status == 6:
        user_list[from_user].query.status -= 4
    else:
        user_list[from_user].query.status -= 1
    if call.data.split(' ')[1] == '1':
        bot.send_message(from_user, 'Выбрана команда Продолжить ' + call.data.split(' ')[0])
        if call.data.split(' ')[0] == '/history':
            history(message, from_user)
        else:
            text_input(message, from_user)
    else:
        end_message = 'Выбрана команда Начать заново ' + call.data.split(' ')[0]
        res = user_list[from_user].query.end_query(bot, user_list, from_user, end_message)
        if res:
            user_list[from_user].command = ''
        if call.data.split(' ')[0] == '/history':
            history(message, from_user)
        else:
            search_price(message, from_user)


@logger.catch()
def question_photo(call: telebot.types.CallbackQuery, bot: telebot.TeleBot, user_list: Dict[int, User],
                   from_user: int) -> None:
    """
    Функция в зависимости от выбора пользователя решает о необходимости запроса количества фотографий
    :param call: callback от бота
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    bot.edit_message_reply_markup(from_user, message_id=call.message.message_id, reply_markup=None)

    if call.data.split()[0] == 'Yes':
        user_list[from_user].query.number_photo = 0
        message = bot.send_message(from_user, 'Необходим вывод фотографий')
    else:
        message = bot.send_message(from_user, 'Вывод фотографий не требуется')
    text_input(message, from_user)


@logger.catch()
def view_history(call: telebot.types.CallbackQuery, bot: telebot.TeleBot, user_list: Dict[int, User],
                 from_user: int) -> None:
    """
    Функция в зависимости от выбора пользователя решает о необходимости запуска запроса из истории
    :param call: callback от бота
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    message = bot.edit_message_reply_markup(from_user, message_id=call.message.message_id,
                                            reply_markup=None)
    if call.data.split('_')[1] != 'Отмена':
        user_list[from_user].command = call.data.split('_')[1]
        repeat_history_key = call.data.split('_')[2]
        repeat_history = user_list[from_user].history.pop(repeat_history_key)
        user_list[from_user].query = repeat_history[1]
        logger.info('Повторный запрос из истории {repeat_history}: команда {comm}, пользователь id:{id}'.format(
            repeat_history=repeat_history, comm=user_list[from_user].command, id=from_user))
        res = del_history(repeat_history_key, from_user)
        if res:
            message.text = ''
            text_input(message, from_user)
    else:
        bot.send_message(message.chat.id, 'История поиска закрыта')
        bot.send_message(message.chat.id,
                         'Команды бота:\n'
                         '/start - запуск бота\n'
                         '/lowprice — вывод самых дешёвых отелей в городе\n'
                         '/highprice — вывод самых дорогих отелей в городе\n'
                         '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                         '/history - история поиска\n')


@logger.catch()
def selection_city(call: telebot.types.CallbackQuery, bot: telebot.TeleBot, user_list: Dict[int, User],
                   from_user: int) -> None:
    """
    Функция в зависимости от выбора пользователя определяет город для поиска или возврат к вводу города
    :param call: callback от бота
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    bot.edit_message_reply_markup(from_user, message_id=call.message.message_id, reply_markup=None)
    if call.data.split('_')[1] != 'repeat':
        user_list[from_user].query.city = \
            list(filter(lambda i_name: i_name['destinationId'] == call.data.split('_')[1],
                        user_list[from_user].query.group_city))[0]
        message = bot.send_message(from_user,
                                   'Вы выбрали ' + user_list[from_user].query.city[
                                       'long_name'])
    else:
        user_list[from_user].query.status = 0
        message = bot.send_message(from_user,
                                   'Вы выбрали повтор поиска города')
        user_list[from_user].query.group_city = None
    text_input(message, from_user)


@logger.catch()
def change_commands_question(message: telebot.types.Message, bot: telebot.TeleBot, user_list: Dict[int, User],
                             from_user: int) -> None:
    """
    Функция выводит клавиатуру запроса от пользователя необходимости смены текущей команды на новую
    :param message: сообщение от бота
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    try:
        bot.edit_message_reply_markup(from_user, message_id=message.id - 1, reply_markup=None)
    except apihelper.ApiTelegramException as a:
        logger.info('попытка убрать клавиатуру, если она была при смене команды')
    keyboard = types.InlineKeyboardMarkup()
    old_command = user_list[from_user].command
    new_command = message.text
    question = 'Вы хотите прервать запрос {old} и начать заново {new}?'.format(
        old=old_command,
        new=new_command)
    keyboard.add(types.InlineKeyboardButton(text='Продолжить {old}'.format(old=old_command),
                                            callback_data=old_command + ' 1'))
    keyboard.add(types.InlineKeyboardButton(text='Начать заново {new}'.format(new=new_command),
                                            callback_data=new_command + ' 0'))
    bot.send_message(from_user, text=question, reply_markup=keyboard)


@logger.catch()
def calendar_input_data(call: telebot.types.CallbackQuery, bot: telebot.TeleBot, user_list: Dict[int, User],
                   from_user: int) -> None:
    """
    Функция в зависимости от выбора пользователя выводит календарь на другой месяц или сохраняет введенную дату
    :param call: callback от бота
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    check_day = 'checkIn_day'
    temp_date = user_list[from_user].query.date_range['now_day'].split('-')
    if user_list[from_user].query.date_range.get('checkIn_day'):
        check_day = 'checkOut_day'
    saved_date = datetime.date(int(temp_date[0]), int(temp_date[1]), int(temp_date[2]))
    month_days = calendar.monthrange(int(temp_date[0]), int(temp_date[1]))[1]
    if call.data == 'next-month':
        saved_date += datetime.timedelta(days=month_days)
        user_list[from_user].query.date_range['now_day'] = saved_date.strftime('%Y-%m-%d')
        markup = create_calendar(saved_date.year, saved_date.month)
        bot.edit_message_text(call.message.text, call.from_user.id, call.message.message_id,
                              reply_markup=markup)
        bot.answer_callback_query(call.id, text='')
    elif call.data == 'previous-month':
        saved_date -= datetime.timedelta(days=month_days)
        user_list[from_user].query.date_range['now_day'] = saved_date.strftime('%Y-%m-%d')
        markup = create_calendar(saved_date.year, saved_date.month)
        bot.edit_message_text(call.message.text, call.from_user.id, call.message.message_id,
                              reply_markup=markup)
        bot.answer_callback_query(call.id, text='')
    elif call.data[0:13] == 'calendar-day-':
        bot.edit_message_reply_markup(from_user, message_id=call.message.message_id, reply_markup=None)
        day = call.data[13:]
        saved_date = datetime.date(int(temp_date[0]), int(temp_date[1]), int(day))
        logger.info('check_day = {check_day}'.format(check_day=check_day))
        user_list[from_user].query.date_range[check_day] = saved_date.strftime('%Y-%m-%d')
        user_list[from_user].query.status += 1
        bot.answer_callback_query(call.id, text='ОК')
        message = bot.send_message(from_user,
                                   'Выбрана дата: {saved_date}'.format(saved_date=saved_date.strftime('%d.%m.%Y')))
        text_input(message, from_user)


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
