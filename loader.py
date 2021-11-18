import os
import telebot
from typing import Dict, Union
from dotenv import load_dotenv
from telebot import TeleBot
from loguru import logger
from playhouse.sqlite_ext import *

logger.add('debug.log', format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}',
           level='DEBUG', rotation='1000 KB', compression='zip', encoding='UTF-8')

load_dotenv()
bot: telebot.TeleBot = TeleBot(os.getenv('token'))
rapidapi_connect: Dict[str, Union[str, Dict[str, str]]] = {
    'url_city': 'https://hotels4.p.rapidapi.com/locations/v2/search',
    'url_hotels': 'https://hotels4.p.rapidapi.com/properties/list',
    'url_photo': 'https://hotels4.p.rapidapi.com/properties/get-hotel-photos',
    'headers': {
        'x-rapidapi-host': 'hotels4.p.rapidapi.com',
        'x-rapidapi-key': os.getenv('rapidapi_key')}}

with SqliteExtDatabase(database='history.db') as db:
    class history_db(Model):
        key = TextField()
        value = JSONField()

        class Meta:
            database = db
    history_db.create_table()
