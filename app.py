import os
import yt_dlp as youtube_dl
import subprocess
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

# Function to download video using yt-dlp
def download_video(url):
    # yt-dlp options
    ydl_opts = {
        'format': 'best',  # Download the best available quality
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Save in downloads folder
        'quiet': True,  # Suppress verbose output
        'ffmpeg_location': '/usr/bin/ffmpeg',  # Ensure ffmpeg is installed
        'retries': 3,  # Retry 3 times on download failure
        'continuedl': True,  # Continue downloading if interrupted
        'noplaylist': True,  # Download only a single video if playlist is provided
    }

    # Create downloads directory if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        # Use yt-dlp to download the video
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
            return file_path, info_dict['title']
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None, None

# Function to compress video using ffmpeg
def compress_video(input_path, output_path):
    try:
        subprocess.run([
            'ffmpeg', '-i', input_path, '-vcodec', 'libx264', '-crf', '28',  # Compression level (CRF)
            '-preset', 'fast', '-y', output_path
        ], check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error compressing video: {str(e)}")
        return None

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle URL messages (video links)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()  # Get the URL sent by the user
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path, video_title = download_video(url)

    # Check if the video was downloaded successfully
    if video_path and os.path.exists(video_path):
        file_size = os.path.getsize(video_path)  # Get file size in bytes

        # If the file is larger than 50MB, attempt to compress it
        if file_size > 50 * 1024 * 1024:  # 50MB in bytes
            await update.message.reply_text("The video is larger than 50MB, compressing it now...")
            compressed_video_path = compress_video(video_path, f"downloads/compressed_{video_title}.mp4")
            
            # Use the compressed video if compression was successful
            if compressed_video_path and os.path.exists(compressed_video_path):
                video_path = compressed_video_path
                file_size = os.path.getsize(video_path)  # Update file size after compression

        # Send the video as a document if it's still too large, or as a video if it's small enough
        if file_size > 50 * 1024 * 1024:  # If the file is still larger than 50MB, send it as a document
            await update.message.reply_text("The video is too large to send as a video. Sending as a document.")
            with open(video_path, 'rb') as video_file:
                await update.message.reply_document(video_file, caption=f"Here is your video (sent as a document): {video_title}")
        else:
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(video_file, caption=f"Here is your video: {video_title}")

        # Clean up by deleting the file after sending
        os.remove(video_path)
    else:
        await update.message.reply_text(f"Error: Unable to download the video from {url}")

def main() -> None:
    # Create the application with webhook
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
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
