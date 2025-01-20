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

# Flask app
app = Flask(__name__)

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Public URL (Koyeb will provide this)
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Target channel ID

if not TOKEN or not WEBHOOK_URL or not CHANNEL_ID:
    raise ValueError("Missing environment variables: BOT_TOKEN, WEBHOOK_URL, or CHANNEL_ID")

# Function to validate URLs
def is_valid_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")

# Function to download video
def download_media(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferredformat': 'mp4'}],
    }

    os.makedirs('downloads', exist_ok=True)  # Ensure the downloads directory exists

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

    video_path = download_media(url)

    if video_path and os.path.exists(video_path):
        try:
            # Upload video to the Telegram channel
            with open(video_path, 'rb') as video:
                await context.bot.send_video(chat_id=CHANNEL_ID, video=video)
            await update.message.reply_text("Video uploaded successfully!")
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            await update.message.reply_text("Failed to upload the video.")
        finally:
            os.remove(video_path)  # Clean up
    else:
        await update.message.reply_text("Failed to download the video. Please try again.")

# Telegram bot setup
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK", 200

@app.route("/")
def home():
    return "Bot is running successfully!", 200

if __name__ == "__main__":
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=8080)  # Use port 8080 for Koyeb