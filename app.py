import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tasks import background_download  # Import the background task

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Start command for the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send a video link to download.")

# Command to download video
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)
    
    if not url:
        await update.message.reply_text("Please provide a valid URL.")
        return

    await update.message.reply_text(f"Downloading video from {url}...")

    # Run the download in the background
    video_path = background_download(url)
    
    if video_path:
        await update.message.reply_text(f"Video downloaded: {video_path}")
        # You can also send the video back to the user
        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(video_file)
    else:
        await update.message.reply_text("Failed to download the video.")

# Main function to run the bot
async def main():
    application = ApplicationBuilder().token('BOT_TOKEN').build()

    # Add the start and download command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))

    # Start the bot
    await application.start()
    await application.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())