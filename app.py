import os
import re
import youtube_dl
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

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

# Google Drive authentication setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
creds = None

# If modifying the scope, delete the token.json file
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
else:
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

drive_service = build('drive', 'v3', credentials=creds)

# Function to upload file to Google Drive
def upload_to_drive(file_path):
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': ['your-folder-id']  # Replace with the folder ID if necessary
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')

    # Make the file public
    drive_service.permissions().create(
        fileId=file_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    # Get the public URL
    download_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    return download_link

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
        await update.message.reply_text("Uploading video to Google Drive...")
        # Upload the video to Google Drive and get the download link
        download_link = upload_to_drive(video_path)
        await update.message.reply_text(f"Download link: {download_link}")
        os.remove(video_path)  # Remove the file after uploading
    else:
        await update.message.reply_text(f"Error: {video_path}")

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()
    # Register handlers
    application.add_handler(CommandHandler("start", start))
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
