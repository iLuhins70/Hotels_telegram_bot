import copy
import datetime
from typing import Dict
from telebot import types
from loader import logger
from loader import history_db


@logger.catch
def open_history(bot: 'telebot.TeleBot', user_list: Dict[int, 'User'], from_user: int) -> None:
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
def save_history(query: 'API_request', user_list: Dict[int, 'User'], from_user: int) -> bool:
    """
    Функция сохранения текущего запроса пользователя
    :param query: сам запрос
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :return: True
    """
    if query.status != 0:
        current_day: datetime = datetime.datetime.utcnow()
        check_day: str = current_day.strftime('%d-%m-%Y %H:%M:%S')
        user_list[from_user].history[check_day] = [user_list[from_user].command, query]
        history_db.create(key=from_user, value=[check_day, user_list[from_user].command,
                                                query_json('to_json', query, user_list[from_user])])
        logger.info('Выполненный запрос пользователя id:{id} сохранен в базу'.format(id=from_user))
    else:
        logger.info(
            'Выполненный запрос пользователя id:{id} не содержит данных и не сохранен в базу'.format(id=from_user))
    return True


@logger.catch
def load_history(user_list: Dict[int, 'User'], from_user: int, temp_query: 'API_request') -> bool:
    """
    Функция загрузки истории запросов пользователя из базы данных
    :param user_list: словарь пользователя
    :param from_user: id пользователя
    :param temp_query: экземпляр класса запрос для временного хранения данных
    :return:
    """
    load_query = history_db.select().where(history_db.key == from_user)
    for i_query in load_query:
        i_temp_query = copy.deepcopy(temp_query)
        user_list[from_user].history[i_query.value[0]] = [i_query.value[1],
                                                          query_json('to_api', i_query.value[2], i_temp_query)]
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
    load_query = history_db.select().where(history_db.key == from_user)
    rec = filter(lambda i_query: i_query.value[0] == repeat_history_key, load_query)
    if rec:
        list(rec)[0].delete_instance()
        logger.info('запись с ключем "{i_key}" найдена и удалена.'.format(i_key=repeat_history_key))
    return True


def query_json(action: str, object_query: 'API_request', api_query: 'API_request'):
    """
    Функция преобразования экземпляра класса в json и наоборот
    :param action: 'to_json' для преобразования экземпляра класса запрос к json формату, в другом случае
                    создание экземпляра класса на основе сохраненных json данных
    :param object_query: экземпляр запроса для сохранения в базу
    :param api_query: экземпляр класса запрос для временного хранения данных
    :return:
    """
    if action == 'to_json':
        json_query = dict()
        json_query['status'] = object_query.status
        json_query['group_city'] = object_query.group_city
        json_query['city'] = object_query.city
        json_query['destination_id'] = object_query.destination_id
        json_query['number_hotels'] = object_query.number_hotels
        json_query['price'] = object_query.price
        json_query['distance'] = object_query.distance
        json_query['date_range'] = object_query.date_range
        json_query['hotels'] = object_query.hotels
        json_query['number_photo'] = object_query.number_photo
        json_query['photos'] = object_query.photos
        json_query['locale'] = object_query.locale
        return json_query
    else:
        api_query.status = object_query['status']
        api_query.group_city = object_query['group_city']
        api_query.city = object_query['city']
        api_query.destination_id = object_query['destination_id']
        api_query.number_hotels = object_query['number_hotels']
        api_query.price = object_query['price']
        api_query.distance = object_query['distance']
        api_query.date_range = object_query['date_range']
        api_query.hotels = object_query['hotels']
        api_query.number_photo = object_query['number_photo']
        api_query.photos = object_query['photos']
        api_query.locale = object_query['locale']
        return api_query
