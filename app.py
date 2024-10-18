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
PORT = int(os.getenv('PORT', 8080))  # Default to 8443 if not set

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to download video using yt-dlp with progress updates and ffmpeg fix
def download_video(url, format_choice='best'):
    download_dir = 'downloads'
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mkv',
        }],
        'ffmpeg_location': '/bin/ffmpeg',
        'progress_hooks': [hook],
        'noplaylist': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return info_dict, os.path.join(download_dir, f"{info_dict['title']}.{info_dict['ext']}")
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
        'youtube.com', 'youtu.be', 'vimeo.com', 'xvideos.com', 
        'xxxymovies.com', 'xhamster.com', 'instagram.com', 'xnxx.com'
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
    await update.message.reply_text("Welcome! Send me a video link to download. You can also choose the quality by sending '/quality'.")

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
        info_dict, _ = download_video(url)
        if not info_dict:
            await update.message.reply_text(f"Error: Could not fetch video information.")
            continue

        await update.message.reply_text("Downloading video...")

        # Download the video
        info_dict, video_path = download_video(url)

        # Check if the video was downloaded successfully
        if os.path.exists(video_path):
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video)
            os.remove(video_path)  # Remove the file after sending
            await auto_delete_file(video_path)  # Schedule file deletion
        else:
            await update.message.reply_text(f"Error: Could not find {video_path}")

# Video quality selection command
async def set_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Choose a video quality:\n1. best\n2. 1080p\n3. 720p\n4. 480p\n\nSend '/quality <choice>' to select."
    )

# Handle video quality selection
async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Please provide a quality choice (1-4).")
        return

    quality_choice = context.args[0]
    if quality_choice == '1':
        context.user_data['quality'] = 'best'
    elif quality_choice == '2':
        context.user_data['quality'] = '137'  # 1080p
    elif quality_choice == '3':
        context.user_data['quality'] = '136'  # 720p
    elif quality_choice == '4':
        context.user_data['quality'] = '135'  # 480p
    else:
        await update.message.reply_text("Invalid choice.")
        return
    await update.message.reply_text(f"Quality set to {context.user_data['quality']}.")

# Auto-delete downloaded files after a set time
async def auto_delete_file(file_path, delay=3600):
    await asyncio.sleep(delay)  # Wait for 1 hour
    if os.path.exists(file_path):
        os.remove(file_path)

# Main function
def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quality", set_quality))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("quality", handle_quality_selection))

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
