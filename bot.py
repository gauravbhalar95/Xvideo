import os
import youtube_dl
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio
import time
from telegram.error import RetryAfter

# Your Telegram bot token
TOKEN = os.environ.get('TOKEN')

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram bot
bot = Bot(token=TOKEN)

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
async def start(update: Update, context):
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context):
    url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")

    video_path = download_video(url)

    if os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.message.reply_video(video)
        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text(f"Error: {video_path}")

# Command to add a channel/group
async def add_channel_group(update: Update, context):
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a valid chat ID (e.g., @your_channel or group ID like -123456789).")
        return

    chat_id = context.args[0].strip()

    try:
        await context.bot.send_message(chat_id=chat_id, text="Channel/group successfully added!")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}. Please check the chat ID and try again.")

# Create the Telegram bot application
application = Application.builder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add_channel_group))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return '', 200

# Set up webhook asynchronously


async def setup_webhook():
    webhook_url = f'https://gorgeous-eloisa-telegramboth-0c5537ec.koyeb.app/webhook'
    while True:
        try:
            await bot.set_webhook(webhook_url)
            print("Webhook set successfully!")
            break
        except RetryAfter as e:
            print(f"Flood control. Retry in {e.retry_after} seconds...")
            time.sleep(e.retry_after)

if __name__ == '__main__':
    # Run webhook setup
    asyncio.run(setup_webhook())

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
