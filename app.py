import os
import youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import nest_asyncio
import logging
from flask import Flask, request

# Enable nested event loops
nest_asyncio.apply()

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for webhook handling
app = Flask(__name__)

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8443))  # Default port for HTTPS
CHANNEL_ID = os.getenv('CHANNEL_ID')

# Ensure required variables are set
if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is required")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is required")
if not CHANNEL_ID:
    raise ValueError("Error: CHANNEL_ID is required")

# Function to download media using youtube-dl
cookies_file = 'cookies.txt'

def download_media(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'cookiefile': cookies_file,
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferredformat': 'mp4'}],
    }

    os.makedirs('downloads', exist_ok=True)

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            file_path = ydl.prepare_filename(info_dict)
            ydl.download([url])
            return file_path
    except Exception as e:
        logger.error(f"Error downloading video: {e}", exc_info=True)
        return None

# Check if the URL is valid
def is_valid_url(url):
    return url.startswith("http://") or url.startswith("https://")

# Telegram bot handlers
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not is_valid_url(url):
        await update.message.reply_text("Invalid URL. Please provide a valid URL.")
        return

    await update.message.reply_text("Downloading...")
    video_path = download_media(url)

    if video_path and os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await context.bot.send_video(chat_id=CHANNEL_ID, video=video)

        os.remove(video_path)
        await update.message.reply_text("Video uploaded successfully!")
    else:
        await update.message.reply_text("Error downloading video.")

# Telegram application setup
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    application.update_queue.put(data)
    return "OK", 200

# Flask server main entry point
@app.route('/')
def index():
    return "Telegram Bot is running.", 200

if __name__ == '__main__':
    # Set webhook
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    # Run Flask app
    app.run(host='0.0.0.0', port=PORT)