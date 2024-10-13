import os
import subprocess
import yt_dlp as youtube_dl
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Initialize Flask app
app = Flask(__name__)

# Telegram bot setup
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Make sure to set this in your environment

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Error: BOT_TOKEN and WEBHOOK_URL must be set")

# Function to download video using yt-dlp
def download_video(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': False,
        'retries': 3,
        'continuedl': True,
        'noplaylist': True,
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict and 'title' in info_dict:
                file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
                return file_path, info_dict['title'], info_dict['ext']
            else:
                return None, None, None
    except Exception as e:
        return None, None, None

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()  # Get the URL sent by the user
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path, video_title, video_ext = download_video(url)

    if video_path and os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.message.reply_video(video, caption=f"Here is your video: {video_title}")
        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text("Error: Unable to download the video. The URL may not be supported or invalid.")

# Webhook endpoint for Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook() -> str:
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.dispatcher.process_update(update)
    return 'ok'

# Set webhook route
@app.route('/set_webhook', methods=['GET'])
def set_webhook() -> str:
    app.bot.setWebhook(WEBHOOK_URL)
    return f'Webhook set to {WEBHOOK_URL}'

# Main function to run the bot
def main() -> None:
    # Create the bot application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Register commands and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot with the Flask app
    application.run_polling()

if __name__ == '__main__':
    main()
