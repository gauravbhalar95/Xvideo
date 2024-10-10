import os
import youtube_dl
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
import logging

# Apply the patch for nested event loops
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Telegram bot token from environment variables
TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    raise ValueError("No TOKEN provided. Set the TOKEN environment variable.")

# Initialize Flask app
app = Flask(__name__)

# Create the Bot instance
bot = Bot(token=TOKEN)

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

# Create the Telegram bot application
application = ApplicationBuilder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask route to handle webhook updates from Telegram
@app.route('/' + TOKEN, methods=['POST'])
def webhook_handler():
    # Process Telegram update
    update = Update.de_json(request.get_json(force=True), bot)
    application.process_update(update)
    return "OK", 200

# Route to set webhook
@app.route('/')
def set_webhook():
    webhook_url = os.getenv('KOYEB_URL') + '/' + TOKEN
    if not webhook_url:
        return "KOYEB_URL not set", 400

    success = bot.set_webhook(webhook_url)
    if success:
        return f"Webhook set to {webhook_url}", 200
    else:
        return "Failed to set webhook", 500

if __name__ == "__main__":
    # Run the Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=True)
