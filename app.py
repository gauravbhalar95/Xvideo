# app.py
import yt_dlp  # Import the yt_dlp library for downloading videos
import os
import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rq import Queue
from redis import Redis
from tasks import background_download  # Import background task

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:your_redis_url_here')
PORT = int(os.getenv('PORT', 8000))

# Redis connection
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue(connection=redis_conn)

# Check bot token
if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")

# Supported platforms regex
YOUTUBE_REGEX = r'^https?://(?:www\.)?(youtube\.com|youtu\.be)'
XHAMSTER_REGEX = r'^https?://(?:www\.)?xhamster\.com'
XVIDEOS_REGEX = r'^https?://(?:www\.)?xvideos\.com'

# Function to check if yt-dlp supports the URL
def is_supported_url(url):
    try:
        ydl = yt_dlp.YoutubeDL()
        result = ydl.extract_info(url, download=False, process=False)
        return result is not None
    except Exception as e:
        logger.error(f"URL not supported: {e}")
        return False

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Received /start command")
    await update.message.reply_text("Welcome! Send me a video link from YouTube, XHamster, or Xvideos to download.")

# Handle pasted URLs and start background job
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    # Check if the URL matches any supported platforms
    if re.match(YOUTUBE_REGEX, url):
        platform = 'YouTube'
    elif re.match(XHAMSTER_REGEX, url):
        platform = 'XHamster'
    elif re.match(XVIDEOS_REGEX, url):
        platform = 'Xvideos'
    else:
        await update.message.reply_text("Please send a valid URL from YouTube, XHamster, or Xvideos.")
        return

    await update.message.reply_text(f"Downloading video from {platform}...")

    # Check if yt-dlp supports the URL
    if not is_supported_url(url):
        await update.message.reply_text(f"Sorry, downloading from {platform} is not supported at the moment.")
        return

    # Enqueue the background download task
    job = queue.enqueue(background_download, url, update.message.chat.id)

    await update.message.reply_text("Video is being processed in the background. You will receive it shortly!")

# Main function to start the bot
def main() -> None:
    # Create the Telegram bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run in webhook or polling mode
    if WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_URL.split('/')[-1],
            webhook_url=WEBHOOK_URL
        )
    else:
        application.run_polling()

if __name__ == '__main__':
    main()