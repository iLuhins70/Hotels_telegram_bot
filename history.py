from typing import Dict, Any
from telebot import types, TeleBot
from loader import logger, History_db
from loader import db
from rapidapi import API_request
from user import User

user_list: Dict[int, User] = dict()


@logger.catch
def open_history(bot: TeleBot, user_list: Dict[int, User], from_user: int) -> None:
    """
    Функция историю запросов пользователя с клавиатурой для выбора необходимости повторного поиска
    :param bot: сам бот
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: None
    """
    history = user_list[from_user].history
    if len(history) > 0:
        bot.send_message(from_user, 'История Ваших запросов:')
        keyboard = types.InlineKeyboardMarkup()
        question = 'Выберите запрос для повторного выполнения'
        logger.info('history: {history}'.format(history=history))
        for num, i_history in enumerate(history, 1):
            i_message = '{num}. {date}\n{command}'.format(
                num=str(num), date=i_history, command=history[i_history][0])
            city = 'не выбран'
            if history[i_history][1].city:
                city = history[i_history][1].city['long_name']
            i_message += '\nГород: {city}'.format(city=city)
            keyboard.add(types.InlineKeyboardButton(text='{num}. {city}'.format(num=str(num), city=city),
                                                    callback_data='history_' + history[i_history][0] + '_' + i_history))
            if history[i_history][1].status == 15:
                i_message += '\nСтатус: завершен'
            else:
                i_message += '\nСтатус: не завершен'
            bot.send_message(from_user, i_message)
        keyboard.add(types.InlineKeyboardButton(text='Отмена', callback_data='history_' + 'Отмена'))
        bot.send_message(from_user, text=question, reply_markup=keyboard)
    else:
        bot.send_message(from_user, 'У Вас пока нет запросов')


@logger.catch
def load_history(user_list: user_list, from_user: int) -> bool:
    """
    Функция загрузки истории запросов пользователя из базы данных
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return:
    """
    with db:
        load_query = History_db.select().where(History_db.key == from_user)
    for i_query in load_query:
        user_list[from_user].history[i_query.value[0]] = [i_query.value[1],
                                                          json_query_(i_query.value[2])]
        logger.info('Загружен запрос {i_query} пользователя id:{id}'.format(i_query=i_query.value[1], id=from_user))
    return True


@logger.catch
def del_history(repeat_history_key: str, from_user: int):
    """
    Функция удаления запроса из истории в случае его повторно запуска
    :param repeat_history_key: дата и время сохраненного запроса
    :param from_user: id пользователя
    :return:
    """
    with db:
        load_query = History_db.select().where(History_db.key == from_user)
    rec = filter(lambda i_query: i_query.value[0] == repeat_history_key, load_query)
    if rec:
        list(rec)[0].delete_instance()
        logger.info('запись с ключем "{i_key}" найдена и удалена.'.format(i_key=repeat_history_key))
    return True


def json_query_(object_query: Dict[str, Any]) -> API_request:
    """ object_query: API_request
    Функция преобразования json в экземпляр класса
    :param object_query: json из базы данных
    :return: экземпляр класса API_request()
    """
    api_query = API_request()
    api_query.status = object_query['status']
    api_query.group_city = object_query['group_city']
    api_query.city = object_query['city']
    api_query.number_hotels = object_query['number_hotels']
    api_query.price = object_query['price']
    api_query.distance = object_query['distance']
    api_query.date_range = object_query['date_range']
    api_query.hotels = object_query['hotels']
    api_query.number_photo = object_query['number_photo']
    api_query.photos = object_query['photos']
    api_query.locale = object_query['locale']
    return api_query
