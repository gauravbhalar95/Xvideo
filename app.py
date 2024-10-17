import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tasks import background_download  # Import background task for downloading videos

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Video Downloader Bot! Send a video link to download.")

# Command to download a video
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = ' '.join(context.args)  # Extract URL from the user's message
    if not url:
        await update.message.reply_text("Please provide a valid video URL.")
        return

    await update.message.reply_text(f"Downloading video from {url}...")

    # Run the download in the background and get the video path
    video_path = await background_download(url)
    
    if video_path:
        await update.message.reply_text(f"Video downloaded successfully: {video_path}")
        # Optionally send the downloaded video back to the user
        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(video_file)
    else:
        await update.message.reply_text("Failed to download the video. Please try again.")

# Main function to run the bot
async def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual Telegram bot token
    bot_token = os.getenv('BOT_TOKEN')
    
    # Build the application
    application = ApplicationBuilder().token(bot_token).build()
    
    # Initialize the application
    await application.initialize()

    # Add handlers for commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))

    # Start polling for updates
    await application.start_polling()
    logger.info("Bot is running...")

    # Keep the bot running until it is stopped
    await application.idle()

# Run the bot
if __name__ == '__main__':
    asyncio.run(main())