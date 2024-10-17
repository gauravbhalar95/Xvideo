import os
import yt_dlp as youtube_dl
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
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,  # Set to True to disable logging, handled by bot
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': format_choice,  # Convert to user-selected format
        }],
        'ffmpeg_location': '/usr/bin/ffmpeg'  # Adjust if needed
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

# Check file size before downloading
def check_file_size(info_dict, max_size_mb=50):
    file_size = info_dict.get('filesize', 0) / (1024 * 1024)  # Convert to MB
    if file_size > max_size_mb:
        return False, file_size
    return True, file_size

# Send video thumbnail before downloading
async def send_thumbnail(update, info_dict):
    thumbnail_url = info_dict.get('thumbnail')
    if thumbnail_url:
        await update.message.reply_photo(photo=thumbnail_url)

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download. You can also choose the quality by sending '/quality'.")

# Handle video links and quality selection
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    # Show downloading message
    await update.message.reply_text("Fetching video information...")

    # Extract video info without downloading
    info_dict, _ = download_video(url, format_choice='best')
    if not info_dict:
        await update.message.reply_text(f"Error: Could not fetch video information.")
        return

    # Send video thumbnail
    await send_thumbnail(update, info_dict)

    # Check file size before downloading
    is_valid, size = check_file_size(info_dict)
    if not is_valid:
        await update.message.reply_text(f"File size ({size:.2f} MB) exceeds the limit.")
        return

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