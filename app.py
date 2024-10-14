import os
import requests
import yt_dlp as youtube_dl
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
import logging

# Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Apply the patch for nested event loops
nest_asyncio.apply()

# Initialize Flask app for the bot
app = Flask(__name__)

# Telegram bot setup
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Ensure this is set in your environment

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Error: BOT_TOKEN and WEBHOOK_URL must be set")

# Function to download video using yt-dlp
def download_media(url):
    logging.debug(f"Attempting to download media from URL: {url}")

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Download best video and audio
        'outtmpl': f'{output_dir}%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'cookiefile': cookies_file,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'ffmpeg_location': '/bin/ffmpeg',
        'socket_timeout': 10,
        'retries': 5,
        'max_filesize': 2 * 1024 * 1024 * 1024,  # Max size 2GB
        'verbose': True,  # Enable verbose logging
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
        return file_path

    except Exception as e:
        logging.error(f"yt-dlp download error: {str(e)}")
        raise


# Function to fetch video links from xVideos
def fetch_xvideos_links(search_query):
    search_url = f"https://www.xvideos.com/search?q={search_query}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    links = []
    for video in soup.find_all('a', class_='video-thumb'):
        video_url = video.get('href')
        if video_url:
            links.append('https://www.xvideos.com' + video_url)
    
    return links

# Function to fetch video links from xHamster
def fetch_xhamster_links(search_query):
    search_url = f"https://xhamster.com/search.php?query={search_query}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    links = []
    for video in soup.find_all('a', class_='video-title'):
        video_url = video.get('href')
        if video_url:
            links.append(video_url)

    return links

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a search query to find videos.")

# Handle pasted URLs or search queries
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    search_query = update.message.text.strip()
    await update.message.reply_text("Fetching video links...")

    xvideos_links = fetch_xvideos_links(search_query)
    xhamster_links = fetch_xhamster_links(search_query)
    
    all_links = xvideos_links + xhamster_links

    if not all_links:
        await update.message.reply_text("No videos found for the given query.")
        return

    # For simplicity, let's just download the first video found
    video_path, video_title = download_video(all_links[0])

    if video_path and os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await update.message.reply_video(video, caption=f"Here is your video: {video_title}")
        os.remove(video_path)  # Remove the video after sending
    else:
        await update.message.reply_text("Error: Unable to download the video.")

# Webhook endpoint for Telegram
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook() -> str:
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.dispatcher.process_update(update)
    return 'ok'

# Set webhook route
@app.route('/set_webhook', methods=['GET'])
def set_webhook() -> str:
    # Manually set the webhook for Telegram
    application = ApplicationBuilder().token(TOKEN).build()
    application.bot.setWebhook(WEBHOOK_URL)
    return f'Webhook set to {WEBHOOK_URL}'

# Health check route
@app.route('/health', methods=['GET'])
def health_check():
    return "Health check OK", 200

# Main function to run the bot
def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    # Run both the health check app and the bot app
    import threading

    # Start the health check app in a separate thread
    health_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8000})
    health_thread.start()

    # Run the main bot application
    main()
