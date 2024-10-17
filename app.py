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
PORT = int(os.getenv('PORT', 8443))  # Default to 8443 if not set

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to download video using yt-dlp with progress updates
def download_video(url, format_choice='best'):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # You can change this to your preferred format
        }],
        'progress_hooks': [hook],
        'noplaylist': True,  # Only download single videos, not playlists
    }


    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return info_dict, os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
    except youtube_dl.utils.DownloadError as e:
        return None, f"DownloadError: {str(e)}"
    except KeyError as e:
        return None, f"KeyError: {str(e)}"
    except Exception as e:
        return None, f"UnknownError: {str(e)}"

# Progress bar function
def download_progress(d):
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
    if parsed_url.netloc in ['www.youtube.com', 'youtu.be', 'vimeo.com', 'xvideos.com', 'xxxymovies.com', 'xhamster.com', 'instagram.com', 'xnxx.com' ]:
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

        # Show fetching message
        await update.message.reply_text("Fetching video information...")

        # Extract video info without downloading
        info_dict, _ = download_video(url, format_choice='best')
        if not info_dict:
            await update.message.reply_text(f"Error: Could not fetch video information.")
            continue

        # Check file size before downloading
        is_valid, size = check_file_size(info_dict)
        if not is_valid:
            await update.message.reply_text(f"File size ({size:.2f} MB) exceeds the limit.")
            continue

        # Send video thumbnail
        await send_thumbnail(update, info_dict)

        # Download the video
        await update.message.reply_text("Downloading video...")
        info_dict, video_path = download_video(url)

        # Check if the video was downloaded successfully
        if os.path.exists(video_path):
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video)
            os.remove(video_path)  # Remove the file after sending
            await auto_delete_file(video_path)  # Schedule file deletion
        else:
            await update.message.reply_text(f"Error: {video_path}")

# Video quality selection command
async def set_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Choose a video quality:\n1. best\n2. 1080p\n3. 720p\n4. 480p\n\nSend '/quality <choice>' to select."
    )

async def handle_quality_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quality_choice = context.args[0]
    if quality_choice == '1':
        context.user_data['quality'] = 'best'
    elif quality_choice == '2':
        context.user_data['quality'] = '137'
    elif quality_choice == '3':
        context.user_data['quality'] = '136'
    elif quality_choice == '4':
        context.user_data['quality'] = '135'
    else:
        await update.message.reply_text("Invalid choice.")
        return
    await update.message.reply_text(f"Quality set to {context.user_data['quality']}.")

# Auto-delete downloaded files after a set time
async def auto_delete_file(file_path, delay=3600):
    await asyncio.sleep(delay)  # Wait for 1 hour
    if os.path.exists(file_path):
        os.remove(file_path)

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quality", set_quality))
    application.add_handler(CommandHandler("quality", handle_quality_selection))
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