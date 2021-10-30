import os
from dotenv import load_dotenv
from telebot import TeleBot
from loguru import logger

logger.add('debug.log', format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}',
           level='DEBUG', rotation='1000 KB', compression='zip', encoding='UTF-8')

load_dotenv()
bot = TeleBot(os.getenv('token'))
rapidapi_connect = {'url_city': 'https://hotels4.p.rapidapi.com/locations/search',
                    'url_hotels': 'https://hotels4.p.rapidapi.com/properties/list',
                    'url_photo': 'https://hotels4.p.rapidapi.com/properties/get-hotel-photos',
                    'headers': {
                        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
                        'x-rapidapi-key': os.getenv('rapidapi_key')}}
