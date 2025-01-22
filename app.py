import os
from flask import Flask, request
from telebot import TeleBot
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8443))  # Default to 8443 if PORT is not set

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Function to download Instagram media
def download_instagram_media(url, chat_id):
    output_path = f"downloads/{chat_id}"  # Save per user
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ydl_opts = {
        "outtmpl": f"{output_path}/%(title)s.%(ext)s",
        "format": "best",
        "quiet": False,
        "cookiefile": "cookies.txt",  # Path to cookies file
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
        return file_path
    except Exception as e:
        return str(e)

# Telegram bot handlers
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me an Instagram story or post URL to download it.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    bot.send_message(message.chat.id, "Downloading media, please wait...")
    file_path = download_instagram_media(url, message.chat.id)
    if os.path.isfile(file_path):
        with open(file_path, "rb") as media:
            bot.send_document(message.chat.id, media)
        os.remove(file_path)  # Clean up after sending
    else:
        bot.send_message(message.chat.id, f"Error: {file_path}")

# Flask route for webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_update():
    json_update = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "OK", 200

# Main function
if __name__ == "__main__":
    # Set webhook
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # Run Flask app
    app.run(host="0.0.0.0", port=PORT)