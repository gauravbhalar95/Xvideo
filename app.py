import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
from mega import Mega  # Import Mega API
import youtube_dl
import asyncio  # Ensure asyncio is imported

# Apply the patch for nested event loops
nest_asyncio.apply()

# Your Telegram bot token and webhook URL from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8443))  # Default to 8443 if not set

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to sanitize the file name
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '', filename)

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
            title = sanitize_filename(info_dict['title'])
            return os.path.join('downloads', f"{title}.{info_dict['ext']}")
    except Exception as e:
        return str(e)

# Function to upload file to Mega.nz
def upload_to_mega(file_path):
    try:
        mega = Mega()
        email = os.getenv('MEGA_EMAIL')
        password = os.getenv('MEGA_PASSWORD')
        m = mega.login(email, password)

        if m is None:
            raise ValueError("Error: Could not login to Mega.nz. Check credentials.")

        uploaded_file = m.upload(file_path)
        link = m.get_upload_link(uploaded_file)
        return link  # Return the link to the uploaded file

    except Exception as e:
        return str(e)

# Function to delete file from Mega.nz
def delete_from_mega(file_link):
    try:
        mega = Mega()
        email = os.getenv('MEGA_EMAIL')
        password = os.getenv('MEGA_PASSWORD')
        m = mega.login(email, password)

        if m is None:
            raise ValueError("Error: Could not login to Mega.nz. Check credentials.")

        # Find file by its link and delete it
        file = m.find(file_link)
        if file:
            m.destroy(file[0])
            return "File deleted successfully."
        else:
            return "File not found."
    except Exception as e:
        return str(e)

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download and upload to Mega.nz.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path = download_video(url)

    # Check if the video was downloaded successfully
    if os.path.exists(video_path):
        await update.message.reply_text("Uploading to Mega.nz...")
        mega_link = upload_to_mega(video_path)

        if "Error" not in mega_link:
            await update.message.reply_text(f"Video uploaded successfully! Here is your link: {mega_link}")
        else:
            await update.message.reply_text(f"Error uploading video: {mega_link}")

        # Optionally delete the local file after upload
        os.remove(video_path)  
    else:
        await update.message.reply_text(f"Error: {video_path}")

# Command to delete a file from Mega.nz
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Please provide the Mega.nz file link to delete.")
        return

    file_link = context.args[0]
    result = delete_from_mega(file_link)
    await update.message.reply_text(result)

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("delete", delete_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Extract the webhook path (the token itself is used as the path)
    url_path = WEBHOOK_URL.split('/')[-1]

    # Start the bot using webhook
    application.run_webhook(
        listen="0.0.0.0",  # Listen on all network interfaces
        port=PORT,  # The port from environment variables
        url_path=url_path,  # Use the path part from WEBHOOK_URL
        webhook_url=WEBHOOK_URL  # Telegram's webhook URL
    )

if __name__ == '__main__':
    main()