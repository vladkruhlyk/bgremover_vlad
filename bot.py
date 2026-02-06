import os
import telebot
from rembg import remove, new_session
from PIL import Image
import io
from flask import Flask
from threading import Thread
import gc

# 1. КОНФИГУРАЦИЯ
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# Глобальная переменная для сессии, но пока пустая!
# Мы не загружаем модель сразу, чтобы сэкономить память при запуске.
session = None 

# --- WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and waiting for photos!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- ЛОГИКА ---
def get_session():
    """Загружает нейросеть только при первом обращении"""
    global session
    if session is None:
        print("Загружаю модель u2netp...") # Лог для отладки
        session = new_session("u2netp")
    return session

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я готов. Отправь фото (первая обработка может занять время).")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        status_msg = bot.reply_to(message, "Обрабатываю... ⏳")
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_image = Image.open(io.BytesIO(downloaded_file))

        # ВОТ ЗДЕСЬ мы вызываем функцию загрузки.
        # Если это первое фото после перезагрузки - тут будет задержка 5-10 сек.
        current_session = get_session()
        
        output_image = remove(input_image, session=current_session)

        bio = io.BytesIO()
        bio.name = 'sticker.png'
        output_image.save(bio, 'PNG')
        bio.seek(0)

        bot.send_document(message.chat.id, bio)
        bot.delete_message(message.chat.id, status_msg.message_id)
        
        # Принудительная очистка мусора в памяти
        gc.collect()

    except Exception as e:
        # Если память кончилась в момент обработки
        bot.reply_to(message, f"Ошибка (возможно не хватило памяти): {e}")
        # Сбрасываем сессию, чтобы попробовать снова
        global session
        session = None
        gc.collect()

if __name__ == '__main__':
    keep_alive()
    bot.polling(non_stop=True)
