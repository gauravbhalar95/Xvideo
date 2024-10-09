import os
import youtube_dl
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Forbidden, BadRequest
import logging

# Your Telegram bot token
TOKEN = '7232982155:AAGShfowEMxo6Mv651w5NMrkiZGiRfeHSmk'

# Dictionary to store user chat IDs for posting downloaded videos
user_chat_ids = {}

# Initialize Flask app
app = Flask(__name__)

# Function to remove existing webhook
def remove_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
    response = requests.get(url)
    if response.status_code == 200:
        print("Webhook removed successfully.")
    else:
        print(f"Failed to remove webhook. Status code: {response.status_code}, Response: {response.text}")

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

# Command to add a channel/group
async def add_channel_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

# Flask route for handling webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return "OK"

# Function to set the new webhook
def set_webhook():
    webhook_url = f"https://your-koyeb-app-url/webhook"  # Replace with your public Koyeb app URL
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Webhook set successfully.")
    else:
        print(f"Failed to set webhook. Status code: {response.status_code}, Response: {response.text}")

# Main function
def main() -> None:
    # Remove the existing webhook
    remove_webhook()

    # Set the new webhook
    set_webhook()

    # Create the application
    global application
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_channel_group))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start Flask server for handling webhook
    app.run(port=5000)

if __name__ == '__main__':
    main()
