from telebot import types
from loader import logger


@logger.catch
def open_history(bot, user_list, from_user):
    history = user_list[from_user].history
    if len(history) > 0:
        bot.send_message(from_user, 'История Ваших запросов:')
        keyboard = types.InlineKeyboardMarkup()

        question = 'Выберите запрос для повторного выполнения'

        for num, i_history in enumerate(history, 1):
            i_message = '{num}. {date}\n{command}'.format(
                num=str(num), date=i_history, command=history[i_history][0])

            city = 'не выбран'
            if history[i_history][1].city != "":
                city = history[i_history][1].city['name']
            i_message += 'Город: {city}'.format(city=city)

            keyboard.add(types.InlineKeyboardButton(text=i_message,
                                                    callback_data='history_' + history[i_history][0] + '_' + i_history))
            if history[i_history][1].status == 7:
                i_message += '\tСтатус: завершен\n'
            else:
                i_message += '\tСтатус: не завершен\n'
            bot.send_message(from_user, i_message)

        keyboard.add(types.InlineKeyboardButton(text='Отмена',
                                                callback_data='history_' + 'Отмена'))
        bot.send_message(from_user, text=question, reply_markup=keyboard)
    else:
        bot.send_message(from_user, 'У Вас пока нет запросов')
