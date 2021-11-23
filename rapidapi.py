from typing import Dict, Any, Optional, Union, Tuple
from loader import logger


@logger.catch
class API_request:
    """
    Класс Запрос. Содержит все данные текущего запроса
    Свойства:
        status: int: Статус запроса, от 0 до 15, необходим для перенаправления выполнения запроса к нужным функциям.
                     Подробнее в функции search из модуля handlers.py
        group_city: Optional[Dict[str, Any]]: Информация о найденных городах
        city: Optional[Dict[str, Any]]: информация о выбранном их списка городе
        number_hotels: int = 0
        price: Dict[str, int] = dict()
        distance: Dict[str, float] = dict()
        date_range: Dict[str, Union[str, int]] = dict()
        hotels: Optional[Dict[str, Any]] = None
        number_photo: Optional[int] = None
        photos: Optional[Dict[str, Any]] = None
        locale: Dict[str, str] = dict()
    """
    def __init__(self) -> None:
        self.status: int = 0
        self.group_city: Optional[Dict[str, Any]] = None
        self.city: Optional[Dict[str, Any]] = None
        self.number_hotels: int = 0
        self.price: Dict[str, int] = dict()
        self.distance: Dict[str, float] = dict()
        self.date_range: Dict[str, Union[str, int]] = dict()
        self.hotels: Optional[Dict[str, Any]] = None
        self.number_photo: Optional[int] = None
        self.photos: Optional[Dict[str, Any]] = None
        self.locale: Dict[str, str] = dict()

    def action_locale(self, action, lang_user='en_US', distance='miles', currency='USD', currency_str='$') -> \
            Tuple[str, str, str]:
        """
        Функция для сохранения и чтения локальных параметров запроса
        :param action: 'save' для записи локальных параметров, иначе загрузка
        :param lang_user: язык ввода
        :param distance: км или мили для измерения расстояния
        :param currency: обозначение валюты
        :param currency_str: строковое представление валюты
        :return:
        """
        if action == 'save':
            self.locale['locale'] = lang_user
            self.locale['distance'] = distance
            self.locale['currency'] = currency
            self.locale['currency_str'] = currency_str
        else:
            lang_user = self.locale['locale']
            currency = self.locale['currency']
            currency_str = self.locale['currency_str']
            return lang_user, currency, currency_str

    def query_json(self) -> Dict[str, Any]:
        """
        Функция преобразования экземпляра класса в json

        :return: json
        """
        json_query = dict()
        json_query['status'] = self.status
        json_query['group_city'] = self.group_city
        json_query['city'] = self.city
        json_query['number_hotels'] = self.number_hotels
        json_query['price'] = self.price
        json_query['distance'] = self.distance
        json_query['date_range'] = self.date_range
        json_query['hotels'] = self.hotels
        json_query['number_photo'] = self.number_photo
        json_query['photos'] = self.photos
        json_query['locale'] = self.locale
        return json_query
