import os
import youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Your Telegram bot token from environment variable
TOKEN = os.getenv('TELEGRAM_TOKEN')

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
        return str(e)

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path = download_video(url)

    # Check if the video was downloaded successfully
    if os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.message.reply_video(video)
        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text(f"Error: {video_path}")

def main() -> None:
    # Create the application
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
