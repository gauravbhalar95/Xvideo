import os
import yt_dlp as youtube_dl
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Your Telegram bot token and webhook URL from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8443))  # Default to 8443 if not set

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to download video using yt-dlp with ffmpeg integration
def download_video(url):
    # yt-dlp options including ffmpeg
    ydl_opts = {
        'format': 'best',  # Download the best available quality
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in downloads folder
        'quiet': True,  # Suppress verbose output
        'ffmpeg_location': '/usr/bin/ffmpeg',  # Ensure ffmpeg is correctly installed
        'retries': 3,  # Retry 3 times on download failure
        'continuedl': True,  # Continue downloading if interrupted
        'noplaylist': True,  # Download only a single video if playlist is provided
    }

    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        # Use yt-dlp to download the video with ffmpeg support
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
            return file_path, info_dict['title']
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None, None

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()  # Get the URL sent by the user
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path, video_title = download_video(url)

    # Check if the video was downloaded successfully
    if video_path and os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.message.reply_video(video, caption=f"Here is your video: {video_title}")
        os.remove(video_path)  # Clean up by deleting the file after sending
    else:
        await update.message.reply_text(f"Error: Unable to download the video from {url}")

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
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
