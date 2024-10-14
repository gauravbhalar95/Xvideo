import os
import logging
import youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
from moviepy.editor import VideoFileClip
import asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your Telegram bot token and webhook URL from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8080))  # Default to 8443 if not set

if not TOKEN:
    logger.error("Error: BOT_TOKEN is not set")
    raise ValueError("BOT_TOKEN is not set")
if not WEBHOOK_URL:
    logger.error("Error: WEBHOOK_URL is not set")
    raise ValueError("WEBHOOK_URL is not set")

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
        logger.error(f"Error downloading video: {e}")
        return None

# Function to check if video exceeds size limit
def is_video_too_large(video_path, max_size_mb=100):
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    return file_size_mb > max_size_mb

# Function to compress video
def compress_video(input_path, output_path, target_size_mb=50):
    clip = VideoFileClip(input_path)
    clip_resized = clip.resize(height=360)  # Resize to lower resolution
    clip_resized.write_videofile(output_path, bitrate="500k")  # Compress the video

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    logger.info(f"Received URL: {url}")
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path = download_video(url)
    compressed_path = "downloads/compressed_video.mp4"

    # Check if the video was downloaded successfully
    if video_path and os.path.exists(video_path):
        # Check if the video is too large to send
        if is_video_too_large(video_path, max_size_mb=50):
            await update.message.reply_text("Video is too large, compressing...")
            compress_video(video_path, compressed_path)

            # Check if compressed video is still too large
            if is_video_too_large(compressed_path, max_size_mb=50):
                await update.message.reply_text("Error: The video is still too large after compression.")
                os.remove(video_path)
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)
                return

            video_path = compressed_path

        with open(video_path, 'rb') as video:
            await update.message.reply_video(video)

        os.remove(video_path)  # Remove the file after sending
        if os.path.exists(compressed_path):
            os.remove(compressed_path)  # Clean up compressed video

        logger.info(f"Video sent and deleted: {video_path}")
    else:
        logger.error(f"Error downloading video: {video_path}")
        await update.message.reply_text("Error downloading video. Please check the URL or try again.")

# Main function
def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Extract the webhook path (the token itself is used as the path)
    url_path = WEBHOOK_URL.split('/')[-1]

    # Start the bot using webhook
    application.run_webhook(
        listen="0.0.0.0",  # Listen on all network interfaces
        port=PORT,  # The port from environment variables
        url_path=url_path,  # Use the path part from WEBHOOK_URL
        webhook_url=WEBHOOK_URL  # Telegram's webhook URL
    )

if __name__ == '__main__':
    main()