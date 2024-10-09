import os
import youtube_dl
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, filters, Dispatcher

# Your Telegram bot token
TOKEN = os.environ.get('TOKEN')  # Use environment variable for the token

# Initialize Flask app
app = Flask(__name__)

# Initialize Telegram bot
bot = Bot(token=TOKEN)

# Dictionary to store user chat IDs for posting downloaded videos
user_chat_ids = {}

# Function to download video using youtube_dl
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Ensure highest quality video download
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
async def start(update: Update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context):
    url = update.message.text.strip()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Downloading video...")

    # Call the download_video function
    video_path = download_video(url)

    # Check if the video was downloaded successfully
    if os.path.exists(video_path):
        with open(video_path, 'rb') as video:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=video)
        os.remove(video_path)  # Remove the file after sending
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {video_path}")

# Command to add a channel/group
async def add_channel_group(update: Update, context):
    if len(context.args) == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide a valid chat ID (e.g., @your_channel or group ID like -123456789).")
        return

    chat_id = context.args[0].strip()

    try:
        # Test sending a message to the chat ID to check if it's valid and the bot has permission
        await context.bot.send_message(chat_id=chat_id, text="Channel/group successfully added!")

        # Store chat ID for this user
        user_chat_ids[update.effective_user.id] = chat_id
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Channel/group {chat_id} added successfully!")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {str(e)}. Please check the chat ID and try again.")

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher = Dispatcher(bot, None, workers=0)

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add", add_channel_group))
    dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    dispatcher.process_update(update)
    return '', 200

if __name__ == '__main__':
    # Set up the webhook
    webhook_url = f'https://gorgeous-eloisa-telegramboth-0c5537ec.koyeb.app/webhook'  # Replace <YOUR_DOMAIN> with your actual domain
    bot.setWebhook(webhook_url)

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)  # You can change the port if needed
