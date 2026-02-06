import os
import telebot
from rembg import remove, new_session
from PIL import Image
import io
from flask import Flask
from threading import Thread

# --- КОНФИГУРАЦИЯ ---
# Токен берем из переменных окружения Render (настроим это позже на сайте)
TOKEN = os.environ.get('BOT_TOKEN')

# Если токена нет, бот упадет с понятной ошибкой
if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Убедись, что добавил его в Environment Variables на Render.")

bot = telebot.TeleBot(TOKEN)

# Инициализируем легкую модель (u2netp), чтобы не вылететь по памяти на бесплатном тарифе
model_name = "u2netp"
session = new_session(model_name)

# --- WEB SERVER (ЧТОБЫ RENDER НЕ УБИЛ ПРОЦЕСС) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    # Render передает порт через переменную PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне картинку, и я сделаю фон прозрачным.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        status_msg = bot.reply_to(message, "Обрабатываю... ⏳")
        
        # 1. Получаем файл
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 2. Открываем картинку
        input_image = Image.open(io.BytesIO(downloaded_file))

        # 3. Удаляем фон (используем заранее загруженную сессию u2netp)
        output_image = remove(input_image, session=session)

        # 4. Сохраняем в буфер
        bio = io.BytesIO()
        bio.name = 'no_bg.png'
        output_image.save(bio, 'PNG')
        bio.seek(0)

        # 5. Отправляем документ
        bot.send_document(message.chat.id, bio)
        
        # Чистим чат от сервисного сообщения
        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.reply_to(message, f"Ошибка при обработке: {e}")

# --- ЗАПУСК ---
if __name__ == '__main__':
    keep_alive() # Запускаем веб-сервер в фоне
    bot.polling(non_stop=True)
