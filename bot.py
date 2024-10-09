import os
import youtube_dl
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import Forbidden, BadRequest
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

# Flask app initialization
app = Flask(__name__)

# Your Telegram bot token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # Replace with your actual webhook URL

# Dictionary to store user chat IDs for posting downloaded videos
user_chat_ids = {}

# Create the application
application = Application.builder().token(TOKEN).build()

# Function to download video using youtube_dl
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
    except Exception as e:
        return str(e)

# Command /start
async def start(update: Update, context) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context) -> None:
    url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path = download_video(url)

    # Check if the video was downloaded successfully
    if os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.message.reply_video(video)
        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text(f"Error: {video_path}")

# Command to add a channel/group
async def add_channel_group(update: Update, context) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a valid chat ID (e.g., @your_channel or group ID like -123456789).")
        return

    chat_id = context.args[0].strip()

    try:
        # Test sending a message to the chat ID
        await context.bot.send_message(chat_id=chat_id, text="Channel/group successfully added!")
        user_chat_ids[update.effective_user.id] = chat_id
        await update.message.reply_text(f"Channel/group {chat_id} added successfully!")
    except Forbidden as e:
        await update.message.reply_text(f"Error: {str(e)}. Bot doesn't have permission to send messages to this chat.")
    except BadRequest:
        await update.message.reply_text("Invalid chat ID or the bot lacks permission to send messages to this chat.")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add_channel_group))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook route for Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)  # Process the update
        return 'OK', 200

# Set webhook when the app starts
@app.before_first_request
def set_webhook():
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logging.info(f"Webhook set to {WEBHOOK_URL}/webhook")

# Test route
@app.route('/')
def home():
    return "Welcome to the Telegram bot with Flask webhook!"

# Main entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
