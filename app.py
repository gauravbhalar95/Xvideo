import os
import yt_dlp as youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import logging
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Flask app for webhook
app = Flask(__name__)

# Function to download ffmpeg binary during runtime
# [ Keep your download_ffmpeg() function here ]

# Telegram bot setup
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8000))  # Heroku provides this

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to download video using yt-dlp with local ffmpeg binary
# [ Keep your download_video() function here ]

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")

    video_path, video_title = download_video(url)

    if video_path and os.path.exists(video_path):
        file_size = os.path.getsize(video_path)

        if file_size > 50 * 1024 * 1024:
            await update.message.reply_text(f"The video is larger than 50MB. Sending it as a document.")
            with open(video_path, 'rb') as video:
                await update.message.reply_document(video, caption=f"Here is your video: {video_title} (sent as a document)")
        else:
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video, caption=f"Here is your video: {video_title}")

        os.remove(video_path)
    else:
        await update.message.reply_text("Error: Unable to download the video. The URL may not be supported.")

# Main bot application
application = ApplicationBuilder().token(TOKEN).build()

# Register command
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Set webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "ok"

# Flask will listen for requests on the specified port
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT)
