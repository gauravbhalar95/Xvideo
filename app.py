import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Command to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send me a video link to download it.")

# Function to download video
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")

    # Set download options for yt-dlp
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Set download directory and filename
        'noplaylist': True,
        'quiet': False,
    }

    # Create downloads directory if it doesn't exist
    os.makedirs('downloads', exist_ok=True)

    try:
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            info_dict = ydl.extract_info(video_url, download=False)
            video_title = info_dict.get('title', 'Video')
            video_file = f'downloads/{video_title}.mp4'

            # Check if the video file exists and send it to the user
            if os.path.exists(video_file):
                await update.message.reply_text(f"Video '{video_title}' downloaded successfully!")
                with open(video_file, 'rb') as video:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=video)
            else:
                await update.message.reply_text("Error: Video file not found after download.")

    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        await update.message.reply_text("Error downloading video. Please check the link and try again.")

# Main function to start the bot
if __name__ == '__main__':
    # Make sure to set your bot's token as an environment variable for security
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Replace with your bot's token if not using an environment variable
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers for commands and messages
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    # Run the bot
    application.run_polling()