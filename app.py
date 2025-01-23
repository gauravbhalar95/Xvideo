import os
import logging
from flask import Flask, request
import telebot
from mega import Mega
import time

# Environment variables
API_TOKEN = os.getenv('BOT_TOKEN')  # Telegram bot token
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Webhook URL
PORT = int(os.getenv('PORT', 8080))  # Default port is 8080

# Initialize the bot
bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mega client
mega_client = None

# Flask app for webhook
app = Flask(__name__)

# Store login status
user_credentials = {}

# Command: /meganz <username> <password>
@bot.message_handler(commands=['meganz'])
def login_mega(message):
    global mega_client
    try:
        # Parse credentials
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Usage: /meganz <username> <password>")
            return
        
        username, password = args[1], args[2]

        # Initialize Mega client and login
        mega = Mega()
        mega_client = mega.login(username, password)
        
        # Save credentials for future sessions
        user_credentials['username'] = username
        user_credentials['password'] = password

        bot.reply_to(message, "✅ Logged into Mega.nz successfully!")
    except Exception as e:
        logger.error(f"Error logging into Mega.nz: {e}")
        bot.reply_to(message, f"❌ Failed to log in: {e}")

# Auto-upload files to Mega.nz
@bot.message_handler(content_types=['document', 'photo', 'video'])
def auto_upload_to_mega(message):
    global mega_client

    if not mega_client:
        bot.reply_to(message, "❌ Please log in first using /meganz <username> <password>.")
        return

    try:
        # Get the file info
        file_id = message.document.file_id if message.content_type == 'document' else \
                  message.photo[-1].file_id if message.content_type == 'photo' else \
                  message.video.file_id

        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_name = file_path.split('/')[-1]

        # Download the file
        downloaded_file = bot.download_file(file_path)
        with open(file_name, 'wb') as f:
            f.write(downloaded_file)

        bot.reply_to(message, "Uploading to Mega.nz, please wait...")

        # Upload to Mega.nz
        uploaded_file = mega_client.upload(file_name)
        public_url = mega_client.get_upload_link(uploaded_file)
        
        bot.reply_to(message, f"✅ File uploaded successfully!\n📎 Public link: {public_url}")
        
        # Clean up local file
        os.remove(file_name)
    except Exception as e:
        logger.error(f"Error uploading to Mega.nz: {e}")
        bot.reply_to(message, f"❌ Failed to upload: {e}")

# Flask routes
@app.route('/' + API_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

@app.route('/')
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + '/' + API_TOKEN, timeout=60)
    return "Webhook set", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)