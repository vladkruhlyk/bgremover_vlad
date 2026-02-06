import os
import telebot
from flask import Flask
from threading import Thread

# 1. КОНФИГУРАЦИЯ
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# --- WEB SERVER (Запускается мгновенно) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- ЛОГИКА БОТА ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Бот готов. Отправь фото.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    # ВАЖНО: Импортируем тяжелые библиотеки только ТУТ, когда фото уже пришло.
    # Это позволяет боту запуститься на Render мгновенно.
    try:
        # Сообщаем пользователю, что начали (первый раз будет долго из-за импорта)
        status_msg = bot.reply_to(message, "Подключаю нейросеть (это может занять время)... ⏳")
        
        # --- ЛЕНИВАЯ ЗАГРУЗКА ---
        from rembg import remove, new_session
        from PIL import Image
        import io
        
        # Загружаем модель (u2netp - легкая)
        session = new_session("u2netp")
        # -------------------------

        bot.edit_message_text("Скачиваю фото... 📥", message.chat.id, status_msg.message_id)
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_image = Image.open(io.BytesIO(downloaded_file))

        bot.edit_message_text("Удаляю фон... ✂️", message.chat.id, status_msg.message_id)
        output_image = remove(input_image, session=session)

        bio = io.BytesIO()
        bio.name = 'no_bg.png'
        output_image.save(bio, 'PNG')
        bio.seek(0)

        bot.send_document(message.chat.id, bio)
        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

# --- ЗАПУСК ---
if __name__ == '__main__':
    keep_alive() # Сразу запускаем веб-сервер, чтобы Render увидел порт
    bot.polling(non_stop=True)
