from telebot import types

def subscribe_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 месяц - 290₽", "3 месяц - 800₽")
    markup.row("6 месяц - 1500₽", "12 месяц - 2500₽")
    return markup

def services_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Добавить товар для отслеживание")
    markup.row("📝 Список товаров")
    return markup