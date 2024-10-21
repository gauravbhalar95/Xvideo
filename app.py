import os
import yt_dlp as youtube_dl
import validators
import requests
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
import asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Your Telegram bot token and webhook URL from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8080))  # Default to 8080 if not set

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to download video using yt-dlp with progress updates and ffmpeg fix
def download_video(url):
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)  # Ensure the directory exists
    cookies_file = 'cookies.txt'

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'cookiefile': cookies_file,
        'postprocessors': [{
            'key': 'FFmpegVideoRemuxer',  # Remux the video to another container format
            'preferedformat': 'mkv',      # Use 'preferedformat' instead of 'preferredformat'
        }],
        'ffmpeg_location': '/bin/ffmpeg',  # Make sure ffmpeg is installed
        'progress_hooks': [hook],
        'noplaylist': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = os.path.join(download_dir, f"{info_dict['title']}.mkv")
            print(f"Downloaded file path: {file_path}")  # Debug log
            return info_dict, file_path
    except youtube_dl.utils.DownloadError as e:
        print(f"DownloadError: {str(e)}")
        return None, None
    except KeyError as e:
        print(f"KeyError: {str(e)}")
        return None, None
    except Exception as e:
        print(f"UnknownError: {str(e)}")
        return None, None

# Progress bar function
def hook(d):
    if d['status'] == 'downloading':
        percent = d['_percent_str']
        eta = d['eta']
        speed = d['_speed_str']
        print(f"Progress: {percent}, Speed: {speed}, ETA: {eta}")

# Validate the URL and check if it's a supported video link
def is_valid_video_link(url):
    if not validators.url(url):
        return False, "Invalid URL"

    parsed_url = urlparse(url)
    supported_sites = [
        'youtube.com', 'youtu.be', 'vimeo.com', 'instagram.com', 
        'xvideos.com', 'xhamster.com', 'xnxx.com'
    ]

    if any(site in parsed_url.netloc for site in supported_sites):
        return True, "Valid video URL"
    return False, "Unsupported video platform"

# Resolve shortened URLs like bit.ly
def resolve_shortened_url(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except requests.RequestException:
        return url

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle video links
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    urls = update.message.text.strip().split()  # Split message to handle multiple URLs

    for url in urls:
        url = resolve_shortened_url(url)

        # Validate URL
        is_valid, message = is_valid_video_link(url)
        if not is_valid:
            await update.message.reply_text(f"Error: {message}")
            continue

        await update.message.reply_text("Fetching video information...")

        # Extract video info and download
        info_dict, video_path = download_video(url)
        if not info_dict or not video_path:
            await update.message.reply_text("Error: Could not fetch video information or download.")
            continue

        await update.message.reply_text("Downloading video...")

        # Check if the video was downloaded successfully
        if os.path.exists(video_path):
            print(f"File exists at path: {video_path}")  # Debug log

            try:
                with open(video_path, 'rb') as video:
                    await update.message.reply_video(video)
                    await update.message.reply_text("Video sent successfully!")
            except Exception as e:
                await update.message.reply_text(f"Error: Failed to send video. {str(e)}")
            finally:
                # Always delete the file whether it was sent successfully or not
                try:
                    os.remove(video_path)
                    print(f"Deleted file at path: {video_path}")  # Debug log
                except Exception as e:
                    print(f"Error deleting file: {str(e)}")
        else:
            print(f"File not found at: {video_path}")  # Debug log
            await update.message.reply_text("Error: Could not find the downloaded video.")

# Main function
def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start webhook
    url_path = WEBHOOK_URL.split('/')[-1]
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=url_path,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()
