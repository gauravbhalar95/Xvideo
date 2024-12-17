import os
import youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import nest_asyncio
from mega import Mega

# Apply the patch for nested event loops
nest_asyncio.apply()

# Your Telegram bot token and webhook URL from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8443))  # Default to 8443 if not set

# Initialize Mega.nz client
mega = Mega()

# State definitions for ConversationHandler
MEGA_EMAIL, MEGA_PASSWORD = range(2)

# Placeholder for storing Mega.nz credentials
mega_credentials = {}

# Debugging: Check if TOKEN and WEBHOOK_URL are retrieved correctly
print(f"TOKEN: {TOKEN}")
print(f"WEBHOOK_URL: {WEBHOOK_URL}")

# Check if TOKEN and WEBHOOK_URL are set
if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")
if not WEBHOOK_URL:
    raise ValueError("Error: WEBHOOK_URL is not set")

# Function to download video using youtube_dl
def download_video(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
        'socket_timeout': 10,
        'retries': 5,
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
    except Exception as e:
        return str(e)

# Function to upload file to Mega.nz
def upload_to_mega(file_path):
    try:
        file = mega.upload(file_path)
        link = mega.get_upload_link(file)
        return link
    except Exception as e:
        return f"Error uploading to Mega.nz: {str(e)}"

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Use /login to set up your Mega.nz account, or send a video link to download and upload.")

# Command: /login
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send your Mega.nz email:")
    return MEGA_EMAIL

# Save Mega.nz email
async def get_mega_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mega_credentials['email'] = update.message.text.strip()
    await update.message.reply_text("Got it! Now, send your Mega.nz password:")
    return MEGA_PASSWORD

# Save Mega.nz password and login
async def get_mega_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mega_credentials['password'] = update.message.text.strip()
    
    try:
        mega.login(mega_credentials['email'], mega_credentials['password'])
        await update.message.reply_text("Successfully logged into Mega.nz!")
    except Exception as e:
        await update.message.reply_text(f"Failed to log in to Mega.nz: {str(e)}")
    return ConversationHandler.END

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not mega_credentials.get('email') or not mega_credentials.get('password'):
        await update.message.reply_text("You must log in to Mega.nz first using /login.")
        return

    if update.message and update.message.text:
        url = update.message.text.strip()
        await update.message.reply_text("Downloading...")

        # Download the file
        file_path = download_video(url)

        if os.path.exists(file_path):
            await update.message.reply_text("Download complete. Uploading to Mega.nz...")
            mega_link = upload_to_mega(file_path)

            if "Error" not in mega_link:
                await update.message.reply_text(f"File uploaded to Mega.nz! Link: {mega_link}")
            else:
                await update.message.reply_text(mega_link)
            os.remove(file_path)  # Cleanup
        else:
            await update.message.reply_text(f"Error: {file_path}")
    else:
        await update.message.reply_text("Please send a valid link.")

def main() -> None:
    # Create application
    application = ApplicationBuilder().token(TOKEN).build()

    # ConversationHandler for Mega.nz login
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            MEGA_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mega_email)],
            MEGA_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mega_password)],
        },
        fallbacks=[],
    )

    # Register handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start bot
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_URL.split('/')[-1],
        webhook_url=WEBHOOK_URL,
    )

if __name__ == '__main__':
    main()