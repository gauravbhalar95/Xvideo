import os
import youtube_dl
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import logging

# Initialize Flask app
app = Flask(__name__)

# Environment variables (replace with your actual environment variables on Koyeb)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'your-telegram-bot-token-here')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'your-koyeb-webhook-url')

# Initialize the bot
bot = Bot(token=TOKEN)

# Function to download video using youtube_dl
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
    }

    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
    except Exception as e:
        return str(e)

# Function to handle messages
async def handle_message(update: Update, context):
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

# Command /start
async def start(update: Update, context):
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Set up webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(), bot)
        application = ApplicationBuilder().token(TOKEN).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Process the update
        application.process_update(update)
        return 'OK', 200

# Set webhook when the app starts
@app.before_first_request
def set_webhook():
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logging.info(f"Webhook set to {WEBHOOK_URL}/webhook")

# Test route
@app.route('/')
def home():
    return 'Welcome to the Telegram bot Flask app!'

# Main entry point for Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
