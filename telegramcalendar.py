from telebot import types
import calendar


def create_calendar(year: int, month: int) -> types.InlineKeyboardMarkup():
    """
    Функция создания клавиатуры для календаря
    :param year: год
    :param month: месяц
    :return: объект клавиатура
    """
    markup = types.InlineKeyboardMarkup()
    row = [types.InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data="ignore")]
    markup.row(*row)
    week_days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    row = []
    for day in week_days:
        row.append(types.InlineKeyboardButton(day, callback_data="ignore"))
    markup.row(*row)
    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(types.InlineKeyboardButton(str(day), callback_data="calendar-day-" + str(day)))
        markup.row(*row)
    row = [types.InlineKeyboardButton("<", callback_data="previous-month"),
           types.InlineKeyboardButton(" ", callback_data="ignore"),
           types.InlineKeyboardButton(">", callback_data="next-month")]
    markup.row(*row)
    return markup
