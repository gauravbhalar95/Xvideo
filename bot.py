import os
import youtube_dl
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import nest_asyncio
import logging

# Apply the patch for nested event loops
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Telegram bot token and webhook URL
TOKEN = os.environ.get('TOKEN')
WEBHOOK_URL = os.getenv('KOYEB_URL') + '/' + TOKEN

# Initialize Flask app
app = Flask(__name__)

# Function to download video using youtube_dl
def download_video(url):
    ydl_opts = {
        'format': 'best',
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

# Create the Telegram bot application
application = ApplicationBuilder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask routes for webhook handling
@app.route('/' + TOKEN, methods=['POST'])
def webhook_handler():
    update = Update.de_json(request.get_json(force=True), bot)
    application.process_update(update)
    return "OK", 200

@app.route('/')
def set_webhook():
    bot = Bot(token=TOKEN)
    bot.delete_webhook()  # Remove any previous webhook
    bot.set_webhook(url=WEBHOOK_URL)
    return f"Webhook set to {WEBHOOK_URL}", 200

if __name__ == "__main__":
    # Start Flask app
    app.run(host='0.0.0.0', port=8000, debug=True)
