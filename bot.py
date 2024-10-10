import os
import youtube_dl
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Initialize Flask app
app = Flask(__name__)

# Your Telegram bot token
TOKEN = os.getenv("TOKEN")  # Use environment variables for the token

# Create the bot application
application = ApplicationBuilder().token(TOKEN).build()

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
    if update.message and update.message.text:
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
    else:
        await update.message.reply_text("Please send a valid URL to download a video.")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)  # Process the update via the bot
    return "OK", 200

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    # Koyeb will give you the public domain for your app
    webhook_url = f"https://{os.getenv('KOYEB_DOMAIN')}/{TOKEN}"
    application.bot.set_webhook(url=webhook_url)
    return "Webhook set!", 200

if __name__ == "__main__":
    # Start the Flask server
    app.run(port=int(os.environ.get("PORT", 5000)), host="0.0.0.0", debug=True)
