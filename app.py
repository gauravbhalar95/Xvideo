import os
import youtube_dl
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Initialize Flask app
app = Flask(__name__)

# Get the Telegram bot token from the environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("Error: BOT_TOKEN environment variable is not set")

# Set up the Telegram application
application = ApplicationBuilder().token(BOT_TOKEN).build()

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

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Telegram webhook route to handle incoming updates
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    """Process incoming updates from Telegram via webhook."""
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)  # Add the update to the queue for processing
    return "OK", 200

# Route to set the webhook for Telegram
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Sets the webhook for the bot to receive updates from Telegram."""
    KOYEB_DOMAIN = os.getenv('KOYEB_DOMAIN')
    if not KOYEB_DOMAIN:
        return "Error: KOYEB_DOMAIN environment variable is not set", 500

    webhook_url = f"https://{KOYEB_DOMAIN}/{BOT_TOKEN}"
    application.bot.set_webhook(url=webhook_url)
    return f"Webhook set successfully to {webhook_url}", 200

# Start the Flask app
if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
