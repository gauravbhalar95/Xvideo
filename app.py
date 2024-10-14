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
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': False,
        'retries': 5,
        'continuedl': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
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
        print(f"Error downloading video: {e}")
        return None, None, None

# Function to process video using FFmpeg
def process_video(input_path, output_path):
    command = ['ffmpeg', '-i', input_path, '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', 
               '-c:a', 'aac', '-b:a', '192k', output_path]
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing video: {e}")
        return False

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")
    video_path, video_title, video_ext = download_video(url)

    if video_path and os.path.exists(video_path):
        output_path = os.path.join('downloads', f"{video_title}_processed.mp4")
        if process_video(video_path, output_path):
            with open(output_path, 'rb') as video:
                await update.message.reply_video(video, caption=f"Here is your processed video: {video_title}")
            os.remove(video_path)
            os.remove(output_path)
        else:
            await update.message.reply_text("Error: Unable to process the video.")
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

# Health check route
@app.route('/')
def health_check():
    return "Healthy", 200

# Main function to run the bot
def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
