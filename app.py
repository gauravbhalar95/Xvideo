import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import youtube_dl
import nest_asyncio

# Apply nested asyncio patch
nest_asyncio.apply()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Environment variables
TOKEN = os.getenv('BOT_TOKEN')  # Your bot token
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Public URL for webhook
PORT = int(os.getenv('PORT', 8443))  # Port for Flask server
CHANNEL_ID = os.getenv('CHANNEL_ID')  # Telegram channel ID for uploads

# Check environment variables
if not TOKEN:
    raise ValueError("BOT_TOKEN is required")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID is required")

# Function to validate URLs
def is_valid_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")

# Function to download video using youtube-dl
def download_media(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferredformat': 'mp4'}],
    }

    # Ensure the downloads directory exists
    os.makedirs('downloads', exist_ok=True)

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            return file_path
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send me a video URL, and I'll download and upload it for you.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("Invalid URL. Please provide a valid video URL.")
        return

    await update.message.reply_text("Downloading your video...")

    # Download video
    video_path = download_media(url)

    if video_path and os.path.exists(video_path):
        try:
            # Upload video to the specified channel
            with open(video_path, 'rb') as video:
                await context.bot.send_video(chat_id=CHANNEL_ID, video=video)
            
            await update.message.reply_text("Video uploaded successfully!")
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            await update.message.reply_text("Failed to upload the video.")
        finally:
            os.remove(video_path)  # Clean up the downloaded file
    else:
        await update.message.reply_text("Failed to download the video. Please try again.")

# Telegram bot setup
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask webhook setup
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK", 200

@app.route("/")
def home():
    return "Telegram Bot is running", 200

# Main entry point
if __name__ == "__main__":
    # Set webhook
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    logger.info("Webhook set successfully")

    # Start Flask server
    app.run(host="0.0.0.0", port=PORT)