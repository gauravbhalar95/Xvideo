import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import nest_asyncio
from mega import Mega  # Import Mega API
import youtube_dl

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

# States for the conversation
EMAIL, PASSWORD, URL = range(3)

# Dictionary to store user credentials
user_credentials = {}

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

# Function to upload file to Mega.nz using credentials
def upload_to_mega(file_path, email, password):
    try:
        mega = Mega()
        m = mega.login(email, password)

        if m is None:
            raise ValueError("Error: Could not login to Mega.nz. Check credentials.")

        uploaded_file = m.upload(file_path)
        link = m.get_upload_link(uploaded_file)
        return link  # Return the link to the uploaded file

    except Exception as e:
        return str(e)

# Start conversation to collect credentials
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Welcome! Please provide your Mega.nz email.")
    return EMAIL

# Collect email
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_credentials[user_id] = {'email': update.message.text}
    
    await update.message.reply_text("Please provide your Mega.nz password.")
    return PASSWORD

# Collect password
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_credentials[user_id]['password'] = update.message.text
    
    await update.message.reply_text("Send me a video link to download and upload to Mega.nz.")
    return URL

# Handle pasted URLs and upload video
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    url = update.message.text.strip()
    
    # Check if user has provided credentials
    if user_id not in user_credentials:
        await update.message.reply_text("Please start the process by using /start.")
        return ConversationHandler.END
    
    email = user_credentials[user_id]['email']
    password = user_credentials[user_id]['password']
    
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path = download_video(url)

    # Check if the video was downloaded successfully
    if os.path.exists(video_path):
        await update.message.reply_text("Uploading to Mega.nz...")
        mega_link = upload_to_mega(video_path, email, password)

        if "Error" not in mega_link:
            await update.message.reply_text(f"Video uploaded successfully! Here is your link: {mega_link}")
        else:
            await update.message.reply_text(f"Error uploading video: {mega_link}")

        # Optionally delete the local file after upload
        os.remove(video_path)  
    else:
        await update.message.reply_text(f"Error: {video_path}")
    
    return ConversationHandler.END

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

    # Define the conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)]
        },
        fallbacks=[]
    )

    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("delete", delete_file))

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