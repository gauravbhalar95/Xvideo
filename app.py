import os
import re
import logging
import yt_dlp  # Use yt-dlp for downloading videos from supported platforms
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
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:your_redis_url_here')
PORT = int(os.getenv('PORT', 8000))

# Set up Redis connection
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue(connection=redis_conn)

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")

# Supported platforms regex
YOUTUBE_REGEX = r'^https?://(?:www\.)?(youtube\.com|youtu\.be)'
XHAMSTER_REGEX = r'^https?://(?:www\.)?xhamster\.com'
XVIDEOS_REGEX = r'^https?://(?:www\.)?xvideos\.com'

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

# Check if yt_dlp supports the URL
def is_supported_url(url):
    ydl = yt_dlp.YoutubeDL()
    result = ydl.extract_info(url, download=False, process=False)
    return result is not None

# Background job for downloading videos
def background_download(url, chat_id):
    video_path = download_video(url)
    return chat_id, video_path

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