import os
import re
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Your Telegram bot token and webhook URL from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8443))  # Default to 8443 if not set
cookies_file = 'cookies.txt'  # Assuming cookies.txt is present in the root directory

# Debugging: Check if TOKEN and WEBHOOK_URL are retrieved correctly
print(f"TOKEN: {TOKEN}")
print(f"WEBHOOK_URL: {WEBHOOK_URL}")

# Check if TOKEN and WEBHOOK_URL are set
if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Regex pattern to capture video title, quality, and duration
video_pattern = r"(1080p)?(.+?)(\d+\smin)"

# Function to download video using yt_dlp with cookies
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best',  # Ensure 1080p or lower
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'cookiefile': cookies_file,  # Use cookie file for authentication
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'socket_timeout': 10,
        'retries': 5,  # Retry on download errors
    }

    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
    except Exception as e:
        return f"Error: {str(e)}"

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link or content with URLs to download.")

# Handle pasted URLs or text content
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text.strip()

    # Search for video URLs or descriptions using regex pattern
    matches = re.findall(video_pattern, message_text)
    
    if not matches:
        await update.message.reply_text("No valid video URLs or descriptions found.")
        return

    for match in matches:
        quality, title, duration = match
        # Assume URL format or extract if it's found in the content
        video_url = f"https://1440pAss fuck and creampie - Homemade compilation 10 min/{title.strip().replace(' ', '_')}"  # Placeholder: Replace with actual URL extraction logic
        await update.message.reply_text(f"Downloading video '{title.strip()}'...")

        # Call the download_video function
        video_path = download_video(video_url)

        # Check if the video was downloaded successfully
        if os.path.exists(video_path):
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video)
            os.remove(video_path)  # Remove the file after sending
        else:
            await update.message.reply_text(f"Error: {video_path}")

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Ensure WEBHOOK_URL is not None before splitting
    if WEBHOOK_URL:
        url_path = WEBHOOK_URL.split('/')[-1]
    else:
        raise ValueError("Error: WEBHOOK_URL is not set or invalid")

    # Start the bot using webhook
    application.run_webhook(
        listen="0.0.0.0",  # Listen on all network interfaces
        port=PORT,  # The port from environment variables
        url_path=url_path,  # Use the path part from WEBHOOK_URL
        webhook_url=WEBHOOK_URL  # Telegram's webhook URL
    )

if __name__ == '__main__':
    main()
