import telebot
import config
import lowprice
import highprice
import bestdeal

bot = telebot.TeleBot(config.token)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Здравствуйте, я Ваш помощник!')


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id,
                     'Команды бота:\n'
                     '/lowprice — вывод самых дешёвых отелей в городе\n'
                     '/highprice — вывод самых дорогих отелей в городе\n'
                     '/bestdeal — вывод отелей, наиболее подходящих по цене и расположению от центра')


@bot.message_handler(commands=['lowprice'])
def search_low_price(message):
    lowprice.search(bot, message)


@bot.message_handler(commands=['highprice'])
def search_high_price(message):
    highprice.search(bot, message)


@bot.message_handler(commands=['bestdeal'])
def search_best_deal(message):
    bestdeal.search(bot, message)


@bot.message_handler(content_types=['text'])
def text_input(message):
    if message.text.lower() == '/hello-world' or 'привет':
        bot.send_message(message.from_user.id, 'Привет, я помогу Вам найти лучший отель! '
                                               'Для вызова помощи наберите /help')


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
