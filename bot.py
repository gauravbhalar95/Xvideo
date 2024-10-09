import os
import youtube_dl
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import Forbidden, BadRequest

# Your Telegram bot token from environment variable
TOKEN = os.getenv('TOKEN')  # Set your bot token as an environment variable
bot = Bot(token=TOKEN)

# Create Flask app
app = Flask(__name__)

# Dictionary to store user chat IDs for posting downloaded videos
user_chat_ids = {}

# Function to download video using youtube_dl
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
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
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: CallbackContext) -> None:
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

# Command to add a channel/group
async def add_channel_group(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Please provide a valid chat ID (e.g., @your_channel or group ID like -123456789).")
        return

    chat_id = context.args[0].strip()

    try:
        # Test sending a message to the chat ID to check if it's valid and the bot has permission
        await context.bot.send_message(chat_id=chat_id, text="Channel/group successfully added!")

        # Store chat ID for this user
        user_chat_ids[update.effective_user.id] = chat_id
        await update.message.reply_text(f"Channel/group {chat_id} added successfully!")
    except Forbidden as e:
        await update.message.reply_text(f"Error: {str(e)}. Bots can't send messages to other bots, or the bot doesn't have permission to send messages to this chat.")
    except BadRequest:
        await update.message.reply_text("Invalid chat ID or the bot lacks permission to send messages to this chat. Please check the chat ID and try again.")

# Flask route for webhook
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

# Set the webhook URL dynamically using an environment variable
def set_webhook():
    # Get the base URL from an environment variable
    base_url = os.getenv('BASE_URL')  # Set your base URL in environment variables
    webhook_url = f'{base_url}/{TOKEN}'
    bot.set_webhook(url=webhook_url)

if __name__ == '__main__':
    # Create the dispatcher
    dispatcher = Dispatcher(bot, None, workers=0)

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add", add_channel_group))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Set the webhook
    set_webhook()

    # Run the Flask app
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
