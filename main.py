import datetime
from telebot import types
from loader import bot
from loader import logger
from rapidapi import API_request
from handlers import search
from history import open_history


class User:

    def __init__(self):
        self.command = ''
        self.query = API_request()
        self.history = dict()  # {date: [command, hotels]}


user_list = dict()
logger.info('Запуск бота.')


@bot.message_handler(commands=['start'])
@logger.catch
def start_message(message, from_user=None):
    if not from_user:
        from_user = message.from_user.id
    if from_user not in user_list:

        user_list[from_user] = User()
        bot.send_message(from_user, 'Здравствуйте, я Ваш помощник!')
        logger.info('Новый пользователь id:{id}'.format(id=from_user))
    else:
        bot.send_message(from_user, 'И снова здравствуйте!')
    help_message(message)


@bot.message_handler(commands=['help'])
@logger.catch
def help_message(message):
    bot.send_message(message.chat.id,
                     'Команды бота:\n'
                     '/start - запуск бота\n'
                     '/lowprice — вывод самых дешёвых отелей в городе\n'
                     '/highprice — вывод самых дорогих отелей в городе\n'
                     '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                     '/history - история поиска\n')


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
@logger.catch
def search_price(message, from_user=None):
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        if user_list[from_user].query.status in [2, 5]:

            try:
                bot.edit_message_reply_markup(from_user, message_id=message.id - 1, reply_markup=None)
            except Exception as a:
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
def history(message, from_user=None):
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
def text_input(message, from_user=None):
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        if user_list[from_user].command == '':
            help_message(message)
        else:
            logger.info('Продолжим поиск.Пользователь id:{id}'.format(id=from_user))
            bot.send_message(from_user, 'Продолжим поиск')
            search(bot, message, user_list, from_user)


@bot.callback_query_handler(func=lambda call: True)
@logger.catch
def callback_worker(call):
    from_user = call.from_user.id
    if from_user in user_list:
        bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="OK!")
        from_user = call.from_user.id
        if call.data.startswith('/'):
            change_command(call, bot, user_list, from_user)
        elif call.data.endswith('photo'):
            question_photo(call, bot, user_list, from_user)
        elif call.data.startswith('history_'):
            view_history(call, bot, user_list, from_user)
        else:
            selection_city(call, bot, user_list, from_user)
    else:
        bot.send_message(from_user, 'Бот был перезапущен, начните сеанс заново /start')


@logger.catch()
def change_command(call, bot, user_list, from_user):
    message = bot.edit_message_reply_markup(from_user, message_id=call.message.message_id,
                                            reply_markup=None)

    message.text = call.data.split(' ')[0]
    if call.data.split(' ')[1] == '1':
        user_list[from_user].query.status -= 1
        bot.send_message(from_user, 'Выбрана команда Продолжить ' + call.data.split(' ')[0])
        if call.data.split(' ')[0] == '/history':
            history(message, from_user)
        else:
            text_input(message, from_user)

    else:
        bot.send_message(from_user, 'Выбрана команда Начать заново ' + call.data.split(' ')[0])
        logger.info(
            'Запись истории запроса: команда {comm}, пользователь id:{id}'.format(comm=user_list[from_user].command,
                                                                                  id=from_user))
        current_day = datetime.datetime.utcnow()

        check_day = current_day.strftime('%d-%m-%Y %H:%M:%S')
        user_list[from_user].query.status -= 1
        user_list[from_user].history[check_day] = [user_list[from_user].command, user_list[from_user].query]

        user_list[from_user].command = ''

        if call.data.split(' ')[0] == '/history':
            history(message, from_user)
        else:
            search_price(message, from_user)


@logger.catch()
def question_photo(call, bot, user_list, from_user):
    bot.edit_message_reply_markup(from_user, message_id=call.message.message_id, reply_markup=None)

    if call.data.split()[0] == 'Yes':
        user_list[from_user].query.number_photo = 0
        message = bot.send_message(from_user, 'Необходим вывод фотографий')
    else:
        message = bot.send_message(from_user, 'Вывод фотографий не требуется')
    text_input(message, from_user)


@logger.catch()
def view_history(call, bot, user_list, from_user):
    message = bot.edit_message_reply_markup(from_user, message_id=call.message.message_id,
                                            reply_markup=None)
    if call.data.split('_')[1] != 'Отмена':
        user_list[from_user].command = call.data.split('_')[1]
        repeat_history_key = call.data.split('_')[2]
        repeat_history = user_list[from_user].history.pop(repeat_history_key)
        user_list[from_user].query = repeat_history[1]
        logger.info('Повторный запрос из истории {repeat_history}: команда {comm}, пользователь id:{id}'.format(
            repeat_history=repeat_history, comm=user_list[from_user].command, id=from_user))
        message.text = ''
        text_input(message, from_user)


@logger.catch()
def selection_city(call, bot, user_list, from_user):
    bot.edit_message_reply_markup(from_user, message_id=call.message.message_id, reply_markup=None)
    if call.data != 'repeat_city':
        user_list[from_user].query.city = \
            list(filter(lambda i_name: i_name['destinationId'] == call.data,
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
def change_commands_question(message, bot, user_list, from_user):
    try:
        bot.edit_message_reply_markup(from_user, message_id=message.id - 1, reply_markup=None)
    except Exception as a:
        logger.info('попытка убрать клавиатуру, если она была при смене команды')
    keyboard = types.InlineKeyboardMarkup()
    old_command = user_list[from_user].command
    new_command = message.text
    keyboard.add(types.InlineKeyboardButton(text='Продолжить {old}'.format(old=old_command),
                                            callback_data=old_command + ' 1'))
    keyboard.add(types.InlineKeyboardButton(text='Начать заново {new}'.format(new=new_command),
                                            callback_data=new_command + ' 0'))
    question = 'Вы хотите прервать запрос {old} и начать заново {new}?'.format(
        old=old_command,
        new=new_command)
    bot.send_message(from_user, text=question, reply_markup=keyboard)


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
