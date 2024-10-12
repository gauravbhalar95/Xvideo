import os
import subprocess

# Function to download ffmpeg binary during runtime
def download_ffmpeg():
    if not os.path.exists('./ffmpeg'):  # Check if ffmpeg is already downloaded
        print("Downloading ffmpeg...")
        # Download the static ffmpeg binary
        try:
            subprocess.run([
                "wget",
                "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz"
            ], check=True)  # Raise an error if the download fails
            # Extract the ffmpeg binary
            subprocess.run(["tar", "-xvf", "ffmpeg-release-i686-static.tar.xz"], check=True)
            # Move the binary to the project root directory
            subprocess.run(["mv", "ffmpeg-*/ffmpeg", "./ffmpeg"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error during ffmpeg download/extraction: {e}")
            return
        # Clean up the unnecessary files
        subprocess.run(["rm", "-rf", "ffmpeg-*"])

# Download ffmpeg at runtime
download_ffmpeg()

# Your existing bot code starts here...
import yt_dlp as youtube_dl
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

# Function to download video using yt-dlp with local ffmpeg binary
def download_video(url):
    ydl_opts = {
        'format': 'best',  # Download the best available quality
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in downloads folder
        'quiet': True,  # Suppress verbose output
        'ffmpeg_location': './ffmpeg',  # Use the local ffmpeg binary
        'retries': 3,  # Retry 3 times on download failure
        'continuedl': True,  # Continue downloading if interrupted
        'noplaylist': True,  # Download only a single video if playlist is provided
    }

    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
            return file_path, info_dict['title']
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None, None

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()  # Get the URL sent by the user
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path, video_title = download_video(url)

    if video_path and os.path.exists(video_path):
        file_size = os.path.getsize(video_path)  # Get file size in bytes

        # Check if the file is larger than 50MB
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            await update.message.reply_text(f"The video is larger than 50MB. Sending it as a document.")
            with open(video_path, 'rb') as video:
                await update.message.reply_document(video, caption=f"Here is your video: {video_title} (sent as a document)")
        else:
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video, caption=f"Here is your video: {video_title}")

        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text("Error: Unable to download the video. The URL may not be supported.")

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
