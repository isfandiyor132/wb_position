from wildberries_parser import wildberries_parser
from datetime import datetime
from threading import Thread
from telebot import types
from markups import *
from config import *
import psycopg2
import telebot
import sqlite3
import time


def main():
    bot = telebot.TeleBot(TOKEN , parse_mode='HTML')

    global stop_keys, title, keys, connect, cursor
    stop_keys = False
    keys = "| "

    connect = psycopg2.connect(DB_URL, sslmode='require')
    cursor = connect.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users( id text, status text, end_status text )""")    
    cursor.execute("""CREATE TABLE IF NOT EXISTS items( id text, title text, link text, key_phrases text, day text, send_date text)""")

    def parsing(id, link, key_phrases, day, send_date):
        while True:
            day = int(day)
            now = datetime.now()
            if send_date == now.strftime("%H:%M"):
                if day < 30:
                    key_phrase = list(map(str, key_phrases.split("|")))[1:-1]
                    bot.send_message(id, f"Парсер запушен на {len(key_phrase)} запросов по вашему клучивым словам")
                    ln_data = wildberries_parser(key_phrases, link)
                    text = ""

                    cursor.execute(f"UPDATE items SET day = '{day+1}' WHERE id = '{id}' AND key_phrases = '{key_phrases}'")
                    connect.commit()

                    if len(ln_data[0]) > 0:
                        text += f"Найдено `{len(ln_data[0])}` позиций:"
                        for i in range(len(ln_data[0])):
                            text += f"\n`{i+1})` Запрос: `{ln_data[0][i]}`,  Позиция:  `{ln_data[1][i]}`"
                        text += "\n\nПозиции проверяется на веб версии сайта и в регионе Москва"
                        bot.send_message(id, f"{text}", parse_mode="MARKDOWNv2")
                    else:
                        bot.send_message(id, "Позиции не найдены")
                    time.sleep(86400)
                    # time.sleep(3600)
                else:
                    cursor.execute(f"DELETE FROM items WHERE id = '{id}' AND key_phrases = '{key_phrases}'")
                    connect.commit()
                    break
            time.sleep(1)

    # Функции для получение данных о товаре
    def add_item(message):
        msg = bot.send_message(message.chat.id, "Отправьте название товара: ")
        bot.register_next_step_handler(msg, add_item_title)

    def add_item_title(message):
        global title
        title = message.text
        msg = bot.send_message(message.chat.id, "Отправьте ариткуль(ссылка) на товар: ")
        bot.register_next_step_handler(msg, add_item_link)

    def add_item_link(message):
        global link
        link = message.text
        msg = bot.send_message(message.chat.id, f"Введите ключевые слова, по которым будет получена позиция:")
        bot.register_next_step_handler(msg, add_item_key)
        
    def add_item_key(message):
        global keys, stop_keys
        if stop_keys:
            now = datetime.now()
            cursor.execute(f'INSERT INTO items(id, title, link, key_phrases, day, send_date) VALUES (?, ?, ?, ?, ?, ?)', (message.chat.id, title, link, keys, "0", now.strftime("%H:%M")))
            connect.commit()
            stop_keys = False
            bot.send_message(message.chat.id, "Товар успешно добавлен в список")
            parsing(message.chat.id, link, keys, 0, now.strftime("%H:%M"))
            keys = "| "
        else:
            key_phrase = list(map(str, keys.split("|")))[1:-1]
            if len(key_phrase) > 40:
                bot.send_message(message.chat.id, f"Максимум количество ключевых слов 41 штук")
            else:
                if len(keys) != 2:
                    bot.delete_message(message.chat.id, message.id-1)
                keys += message.text + " | "
                markup = types.InlineKeyboardMarkup(row_width=2)
                item1 = types.InlineKeyboardButton("📋 Добавить товар в список", callback_data="addItem")
                markup.add(item1)
                msg = bot.send_message(message.chat.id, f"Ключевие слова: {keys}", reply_markup=markup)
                bot.register_next_step_handler(msg, add_item_key)

    # Функции для проверки регистрации пользователя
    def is_valid(message):
        global connect, cursor
        cursor.execute(f"SELECT id FROM users WHERE id = '{message.chat.id}'")
        id = cursor.fetchone()
        if not id:
            is_valid = False
        else:
            is_valid = True
        return is_valid

    # Функции для проверки активно ли аккаунт
    def is_active(id):
        global connect, cursor
        cursor.execute(f"SELECT * FROM users WHERE id = '{id}'")
        user_data = cursor.fetchone()
        end_sub_date = user_data[2]
        data = end_sub_date.split("-")
        end_hour, end_minute = map(int, data[0].split(":"))
        end_month, end_day, end_year = map(int, data[1].split("/"))
        now = datetime.now()
        date = datetime(end_year, end_month, end_day, end_hour, end_minute)
        if (now-date).days >= 0:
            is_active = False 
        else:
            is_active = True
        return is_active

    # Функции для проверки есть ли такой товар
    def is_item_exist(message, title):
        global connect, cursor
        cursor.execute(f"SELECT * FROM items WHERE id = '{message.chat.id}' AND title = '{title}'")
        items = cursor.fetchone()
        if not items:
            is_item_exist = False
        else:
            is_item_exist = True
        return is_item_exist


    @bot.message_handler(commands=['start'])
    def start(message):
        global connect, cursor
        try:
            id = message.chat.id
            if not is_valid(message):
                month_days = [31,28,31,30,31,30,31,31,30,31,30,31]
                now = datetime.now()
                day = now.day
                hour = now.hour 
                minute = now.minute
                year = now.year
                month = now.month
                if month+1 > 12:
                    month= (month+1)-12
                    year+=1
                else:
                    month += 1
                day = day+30-month_days[month-1]
                end_sub_date = f"{hour}:{minute}-{month}/{day}/{year}"  
                cursor.execute(f'INSERT INTO users(id, status, end_status) VALUES (?, ?, ?)', (id, "Бесплатный", end_sub_date,))
                connect.commit()
                bot.send_message(message.chat.id, f"Добро пожаловать в бота, в котором вы можете автоматизировать анализ данных из *Wildberries*\n\nВы получили месяц `Бесплатного` подписки", parse_mode="MARKDOWNv2", reply_markup=services_menu())  
            elif not is_active(message.chat.id):
                bot.send_message(message.chat.id, f"Добро пожаловать в бота, в котором вы можете автоматизировать анализ данных из *Wildberries*\n\nВаша подписка закончилась купите подписку чтобы пользоваться ботом", parse_mode="MARKDOWNv2", reply_markup=subscribe_menu())  
            else:
                cursor.execute(f"SELECT * FROM users WHERE id = '{id}'")
                user_data = cursor.fetchone()
                status = user_data[1]
                end_sub_date = user_data[2]
                bot.send_message(message.chat.id, f"Приветсвую вас в боте в которым вы можете автомизировать анализ данных из *Wildberries*\n\nУ вас `{status}` подписка до `{end_sub_date}`", parse_mode="MARKDOWNv2", reply_markup=services_menu())
        except Exception as exp:
            print(exp)            
            bot.send_message(message.chat.id, f"⚠️ Ошибка загрузки")


    @bot.message_handler(content_types=['text'])
    def text_check(message):
        global connect, cursor
        try:
            if not is_valid(message):
                month_days = [31,28,31,30,31,30,31,31,30,31,30,31]
                now = datetime.now()
                day = now.day
                hour = now.hour 
                minute = now.minute
                year = now.year
                month = now.month
                if month+1 > 12:
                    month= (month+1)-12
                    year+=1
                else:
                    month += 1
                day = day+30-month_days[month-1]
                end_sub_date = f"{hour}:{minute}-{month}/{day}/{year}"  
                cursor.execute(f'INSERT INTO users(id, status, end_status) VALUES (?, ?, ?)', (message.chat.id, "Бесплатный", end_sub_date,))
                connect.commit()
                bot.send_message(message.chat.id, f"Добро пожаловать в бота, в котором вы можете автоматизировать анализ данных из *Wildberries*\n\nВы получили месяц `Бесплатного` подписки", parse_mode="MARKDOWNv2")  
            elif not is_active(message.chat.id):
                bot.send_message(message.chat.id, f"Ваша подписка закончилась купите подписку чтобы пользоваться ботом дальше", parse_mode="MARKDOWNv2", reply_markup=subscribe_menu())  
            elif "₽" in message.text:
                period, price = map(str, message.text.split(" - "))
                price = price.replace("₽", "")
                bot.send_invoice(
                    chat_id=message.chat.id,
                    title=f'Купить подписку на {period}',
                    description="После оплаты в ваш аккаунт сразу активируются",
                    invoice_payload=period,
                    provider_token=PAYMASTER_TOKEN,
                    currency='RUB',
                    photo_url='https://md-gazeta.ru/wp-content/uploads/2020/09/EFTPOS-machine_AdobeStock_smaller_140072541-scaled.jpg',
                    photo_height=256,
                    photo_width=512,
                    photo_size=512,
                    prices = [types.LabeledPrice(label=f"Подписку на {period}", amount=int(price)*100)],    
                    is_flexible=False,
                    start_parameter='WILDBERRIES-SUBSCRIBE'
                )
            elif message.text == "➕ Добавить товар для отслеживание":
                add_item(message)
            elif message.text == "📝 Список товаров":
                cursor.execute(f"SELECT * FROM items WHERE id = '{message.chat.id}'")
                data = cursor.fetchall()[::-1]
                ln_data = len(data)

                if ln_data > 0:
                    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
                    while ln_data != 0:
                        if ln_data > 3:
                            markup.row(data[ln_data-1][1], data[ln_data-2][1], data[ln_data-3][1])
                            ln_data -= 3
                        elif ln_data == 2:
                            markup.row(data[ln_data-1][1], data[ln_data-2][1])
                            ln_data -= 2
                        else:
                            markup.row(data[ln_data-1][1])
                            ln_data -= 1
                    markup.row("⬅️ Назад")

                    bot.send_message(message.chat.id, f"У вас сейчас в аккаунте {len(data)} добавленных товаров:", reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, "У вас сейчас аккаунте нет товаров")
            elif message.text == "⬅️ Назад":
                bot.send_message(message.chat.id, "🏠 Главный меню", reply_markup=services_menu())
            elif is_item_exist(message, message.text):
                markup = types.InlineKeyboardMarkup(row_width=2)
                item1 = types.InlineKeyboardButton("Удалить товар", callback_data=f"delete_{message.text}")
                markup.add(item1)
                bot.send_message(message.chat.id, f"Выберите действия: ", reply_markup=markup)

        except Exception as exp:
            print(exp)
            bot.send_message(message.chat.id, f"⚠️ Ошибка загрузки")


    @bot.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


    @bot.message_handler(content_types=['successful_payment'])
    def successful_payment(message):
        id = message.chat.id
        period = int(message.successful_payment.invoice_payload.replace(" месяц", ""))
        month_days = [31,28,31,30,31,30,31,31,30,31,30,31]
        bot.send_message(message.chat.id, f'Оплата прошла успешно\n\nВаш статус изменён на `Платный`', parse_mode='MARKDOWNv2', reply_markup=services_menu())
        now = datetime.now()
        day = now.day
        hour = now.hour 
        minute = now.minute
        year = now.year
        month = now.month
        if month+period > 12:
            month= (month+period)-12
            year+=1
        else:
            month += period
        day = day+(period*30)-sum(month_days[month-1:period+1])

        end_sub_date = f"{hour}:{minute}-{month}/{day}/{year}"  
        cursor.execute(f"UPDATE users SET status = 'Платный' WHERE id = '{id}'")
        cursor.execute(f"UPDATE users SET end_status = '{end_sub_date}' WHERE id = '{id}'")
        connect.commit()


    # Функции для обработки call_back запросов     
    @bot.callback_query_handler(func=lambda call: True)
    def callback_check(call):
        global stop_keys, cursor, connect
        try:
            if "addItem" == call.data:
                stop_keys = True
                bot.send_message(call.message.chat.id, "Отправьте любое сообщение для подтверждения создания товара")
            elif "delete" in call.data:
                call.data, msg_text = map(str, (call.data).split('_'))
                cursor.execute(f"DELETE FROM items WHERE id = '{call.message.chat.id}' AND title = '{msg_text}'")
                connect.commit()
                bot.send_message(call.message.chat.id, "Товар удален из вашего аккаунта")

        except Exception as exp:
            print(exp)
            bot.send_message(call.message.chat.id, f"⚠️ Ошибка загрузки")


    cursor.execute(f"SELECT * FROM items")
    all_data = cursor.fetchall()
    for info in all_data:
        if is_active(info[0]):
            th = Thread(target=parsing, args=(info[0], info[2], info[3], info[4], info[5],))
            th.start()
        else:
            bot.send_message(info[0], f"Добро пожаловать в бота, в котором вы можете автоматизировать анализ данных из *Wildberries*\n\nВаша подписка закончилась купите подписку чтобы пользоваться ботом", parse_mode="MARKDOWNv2", reply_markup=subscribe_menu()) 
            break 


    bot.polling(non_stop=True)

if __name__ == "__main__":
    main()