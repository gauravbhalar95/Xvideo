import os
import re
import logging
import yt_dlp  # Use yt-dlp for downloading YouTube videos
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from rq import Queue
from redis import Redis

# Apply patch for nested event loops (needed in some environments)
nest_asyncio.apply()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Telegram bot token from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:b9pTqUrpgEYvUKcJM3XT3FqpgOyJAX7w@redis-13753.c212.ap-south-1-1.ec2.redns.redis-cloud.com:13753')
PORT = int(os.getenv('PORT', 8000))

# Set up Redis connection
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue(connection=redis_conn)

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")

# Function to sanitize file name for saving
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '', filename)

# Function to download the video using yt_dlp
def download_video(url):
    ydl_opts = {
        'format': 'best[filesize<=50M]',  # Limit the video size to 50 MB
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Convert to mp4 format
        }],
        'ffmpeg_location': '/bin/ffmpeg',  # Path to ffmpeg binary (ensure it's installed)
    }

    # Ensure the downloads directory exists
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = sanitize_filename(info_dict['title'])
            return os.path.join('downloads', f"{title}.{info_dict['ext']}")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Background job for downloading videos
def background_download(url, chat_id):
    video_path = download_video(url)
    return chat_id, video_path

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Received /start command")
    await update.message.reply_text("Welcome! Send me a YouTube video link to download.")

# Handle pasted URLs and start background job
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    # Check if the URL is a valid YouTube link
    if not re.match(r'^https?://(?:www\.)?youtube\.com|youtu\.be', url):
        await update.message.reply_text("Please send a valid YouTube URL.")
        return

    await update.message.reply_text("Downloading video...")

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

    # Check if a webhook URL is set, and run in webhook mode if it is
    if WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_URL.split('/')[-1],
            webhook_url=WEBHOOK_URL
        )
    else:
        # Start the bot with polling
        application.run_polling()

if __name__ == '__main__':
    main()