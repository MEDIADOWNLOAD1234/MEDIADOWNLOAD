import os
import time
import threading
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import yt_dlp

# --- 1. ВЕБ-СЕРВЕР ДЛЯ RENDER ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Fake Web Server listening on port {port}")
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- 2. ПОЛУЧЕНИЕ ТОКЕНА ---
# Закодируйте ваш новый токен из BotFather на сайте base64encode.org и вставьте сюда:
ENCODED_TOKEN = "ODkyODcwMDYyODpBQUdwbFdhTHpoRVNVQmxjbjFmMlNMdG40aW9oZm5lZS1vOA=="

try:
    DECODED_TOKEN = base64.b64decode(ENCODED_TOKEN).decode('utf-8').strip()
except Exception:
    DECODED_TOKEN = ""

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip() or DECODED_TOKEN

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_urls = {}

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет! Я бот для загрузки медиа 🎬🎵\n\n"
        "Отправь мне ссылку на видео (TikTok, Reels, Shorts, YouTube), "
        "и я помогу скачать его без водяных знаков или сохранить в MP3!",
    )

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "Пожалуйста, отправь корректную ссылку.")
        return

    user_urls[message.chat.id] = url

    markup = InlineKeyboardMarkup()
    btn_video = InlineKeyboardButton(
        "🎬 Видео (без водяного знака)", callback_data="dl_video"
    )
    btn_audio = InlineKeyboardButton("🎵 Аудио (MP3)", callback_data="dl_audio")
    markup.add(btn_video)
    markup.add(btn_audio)

    bot.reply_to(
        message, "Выберите, что вы хотите скачать:", reply_markup=markup
    )

@bot.callback_query_handler(
    func=lambda call: call.data in ["dl_video", "dl_audio"]
)
def process_download(call):
    chat_id = call.message.chat.id
    url = user_urls.get(chat_id)

    if not url:
        bot.answer_callback_query(
            call.id, "Ссылка устарела. Отправьте ее снова."
        )
        return

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "⏳ Загрузка и обработка файла...",
        chat_id=chat_id,
        message_id=call.message.message_id,
    )

    mode = call.data

    if mode == "dl_audio":
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": f"downloads/{chat_id}_%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }
    else:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": f"downloads/{chat_id}_%(id)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }

    try:
        os.makedirs("downloads", exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Медиафайл")
            ext = "mp3" if mode == "dl_audio" else "mp4"
            file_id = info.get("id")
            file_path = f"downloads/{chat_id}_{file_id}.{ext}"

            if not os.path.exists(file_path):
                file_path = ydl.prepare_filename(info)
                if mode == "dl_audio":
                    file_path = os.path.splitext(file_path)[0] + ".mp3"

        bot.edit_message_text(
            "📤 Отправка файла в чат...",
            chat_id=chat_id,
            message_id=call.message.message_id,
        )

        with open(file_path, "rb") as file:
            if mode == "dl_audio":
                bot.send_audio(
                    chat_id, file, title=title, caption=f"🎵 {title[:50]}"
                )
            else:
                bot.send_video(
                    chat_id,
                    file,
                    caption=f"🎬 {title[:50]}",
                    supports_streaming=True,
                )

        if os.path.exists(file_path):
            os.remove(file_path)

        bot.delete_message(
            chat_id=chat_id, message_id=call.message.message_id
        )

    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        bot.edit_message_text(
            "❌ Произошла ошибка при загрузке. Проверьте ссылку.",
            chat_id=chat_id,
            message_id=call.message.message_id,
        )

if __name__ == "__main__":
    print("Бот-загрузчик запущен!")
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Ошибка при удалении вебхука: {e}")
    time.sleep(1)
    bot.infinity_polling(timeout=20, long_polling_timeout=5)

        with
