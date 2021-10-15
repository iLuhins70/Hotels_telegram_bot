import datetime
from telebot import types
from loader import bot
from rapidapi import API_request
from handlers import search
from history import open_history



class User:

    def __init__(self):
        self.command = ''
        self.query = API_request()
        self.history = dict()  # {date: [command, hotels]}


user_list = dict()


@bot.message_handler(commands=['start'])
def start_message(message, from_user=None):
    if message.from_user.id not in user_list:
        from_user = message.from_user.id
        user_list[from_user] = User()
        bot.send_message(from_user, 'Здравствуйте, я Ваш помощник!')
    else:
        bot.send_message(from_user, 'И снова здравствуйте!')

    help_message(message)


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id,
                     'Команды бота:\n'
                     '/start - запуск бота\n'
                     '/lowprice — вывод самых дешёвых отелей в городе\n'
                     '/highprice — вывод самых дорогих отелей в городе\n'
                     '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра\n'
                     '/history - история поиска\n'
                     '/hello-world или "привет" - приветствие по ТЗ')


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def search_price(message, from_user=None):
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        if user_list[from_user].query.status in [2, 5]:
            print('надо убрать кнопки', user_list[from_user].query.status)
            bot.edit_message_reply_markup(from_user, message_id=message.id - 1, reply_markup=None)

        if user_list[from_user].command == '':

            
            user_list[from_user].query = API_request()
            user_list[from_user].command = message.text
            user_list[from_user].query.status = 0
            search(bot, message, user_list, from_user)
        else:
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


@bot.message_handler(commands=['history'])
def history(message, from_user=None):
    if not from_user:
        from_user = message.from_user.id
    if from_user in user_list:
        open_history(bot, message, user_list, from_user)


@bot.message_handler(content_types=['text'])
def text_input(message, from_user=None):

    if not from_user:
        from_user = message.from_user.id

    print(message.text)
    if message.text.lower() == '/hello-world': # or 'привет':
        bot.send_message(from_user, 'Привет, я помогу Вам найти лучший отель! '
                                               'Для вызова помощи наберите /help')
    elif from_user in user_list:
        print('user_list[from_user].query.status =', user_list[from_user].query.status)
        bot.send_message(from_user, 'Продолжим поиск')
        search(bot, message, user_list, from_user)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    from_user = call.from_user.id
    if from_user in user_list:
        bot.answer_callback_query(callback_query_id=call.id, show_alert=False, text="OK!")
        from_user = call.from_user.id
        if call.data.startswith('/'):

            message = bot.edit_message_reply_markup(from_user, message_id=call.message.message_id,
                                                    reply_markup=None)

            message.text = call.data.split(' ')[0]
            if call.data.split(' ')[1] == '1':
                user_list[from_user].query.status -= 1
                bot.send_message(from_user, 'Выбрана команда Продолжить ' + call.data.split(' ')[0])
                text_input(message, from_user)
                print('продолжить', user_list[from_user].query.status)
            else:
                bot.send_message(from_user, 'Выбрана команда Начать заново ' + call.data.split(' ')[0])
                current_day = datetime.datetime.utcnow()

                check_day = current_day.strftime('%d-%m-%Y %H:%M:%S')
                user_list[from_user].query.status -= 1
                user_list[from_user].history[check_day] = [user_list[from_user].command, user_list[from_user].query]

                user_list[from_user].command = ''

                search_price(message, from_user)
        elif call.data.endswith('photo'):
            bot.edit_message_reply_markup(from_user, message_id=call.message.message_id, reply_markup=None)

            if call.data.split()[0] == 'Yes':
                user_list[from_user].query.number_photo = 0
                message = bot.send_message(from_user, 'Необходим вывод фотографий')
            else:
                message = bot.send_message(from_user, 'Вывод фотографий не требуется')
            text_input(message, from_user)
        elif call.data.startswith('history_'):
            message = bot.edit_message_reply_markup(from_user, message_id=call.message.message_id,
                                                    reply_markup=None)
            if call.data.split('_')[1] != 'Отмена':
                user_list[from_user].command = call.data.split('_')[1]
                user_list[from_user].query = user_list[from_user].history[call.data.split('_')[2]][1]
                message.text =''
                text_input(message, from_user)
        else:

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
    else:
        bot.send_message(from_user, 'Бот был перезапущен, начните сеанс заново /start')


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
