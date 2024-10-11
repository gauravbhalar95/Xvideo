import os
import yt_dlp as youtube_dl
import requests  # For handling Terabox links
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

# Helper function to identify if the URL is a Terabox link
def is_terabox_link(url):
    return "terabox.com" in url or "dubox.com" in url

# Function to handle Terabox file download using requests
def download_terabox_file(url):
    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        # Use requests to download the file
        response = requests.get(url, stream=True)
        file_name = url.split('/')[-1]  # Get file name from the URL
        file_path = os.path.join('downloads', file_name)

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        return file_path, file_name
    except Exception as e:
        print(f"Error downloading Terabox file: {str(e)}")
        return None, None

# Function to download video using yt-dlp or handle Terabox link
def download_video(url):
    if is_terabox_link(url):
        return download_terabox_file(url)

    # yt-dlp handling for videos
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}"), info_dict['title']
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None, None

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link or Terabox link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    await update.message.reply_text("Downloading...")

    # Call the download_video function (which now also handles Terabox links)
    file_path, file_title = download_video(url)

    # Check if the file was downloaded successfully
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            await update.message.reply_document(file, caption=f"Here is your file: {file_title}")
        os.remove(file_path)  # Clean up the file after sending
    else:
        await update.message.reply_text(f"Error: Unable to download the file from {url}")

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
