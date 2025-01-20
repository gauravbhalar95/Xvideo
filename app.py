import os
import logging
from yt_dlp import YoutubeDL
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import nest_asyncio

# Enable nested asyncio
nest_asyncio.apply()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Replace with your Telegram bot token
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Replace with your public webhook URL

# Validate environment variables
if not BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL")

# yt-dlp download function
def download_video(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    os.makedirs('downloads', exist_ok=True)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            return file_path
    except Exception as e:
        logger.error(f"Failed to download video: {e}")
        return None

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a valid video URL to download the video."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Validate URL
    if not url.startswith(("http://", "https://")):  # Check for both http and https
        await update.message.reply_text("Please provide a valid URL!")
        return

    await update.message.reply_text("Downloading your video, please wait...")

    # Download video
    video_path = download_video(url)

    if video_path:
        try:
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video=video)
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
            await update.message.reply_text("Failed to send the downloaded video.")
        finally:
            os.remove(video_path)  # Clean up after sending
    else:
        await update.message.reply_text("Failed to download the video. Please try again later.")

# Setup the bot application
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))  # Add echo handler for testing

# Flask webhook endpoint
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.update_queue.put(update)  # Await the put operation
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running!", 200

# Ensure the webhook is set
async def set_webhook():
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    # Set the webhook
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host="0.0.0.0", port=8080, debug=True)  # Enable debug mode
