import os
import subprocess
import yt_dlp as youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

# Path to the static ffmpeg binary
FFMPEG_PATH = '/bin/ffmpeg'  # Set the correct path for ffmpeg

# Telegram bot setup
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")

# Function to download video using yt-dlp
def download_video(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'ffmpeg_location': FFMPEG_PATH,  # Specify local ffmpeg binary
        'retries': 3,
        'continuedl': True,
        'noplaylist': True,
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
            return file_path, info_dict['title'], info_dict['ext']
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None, None, None

# Function to compress video using ffmpeg
def compress_video(input_path, output_path):
    command = [FFMPEG_PATH, '-i', input_path, '-vcodec', 'libx264', '-crf', '28', output_path]
    subprocess.run(command, check=True)

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download.")

# Handle pasted URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()  # Get the URL sent by the user
    await update.message.reply_text("Downloading video...")

    # Call the download_video function
    video_path, video_title, video_ext = download_video(url)

    if video_path and os.path.exists(video_path):
        file_size = os.path.getsize(video_path)  # Get file size in bytes

        # Check if the file is larger than 100MB
        if file_size > 1024 * 1024 * 1024:  # 100MB limit
            await update.message.reply_text(f"The video is larger than 100MB. Compressing it...")

            # Create a path for the compressed video
            video_compressed_path = os.path.join('downloads', f"compressed_{video_title}.mp4")
            
            # Compress the video
            compress_video(video_path, video_compressed_path)

            # Replace video_path with video_compressed_path
            if os.path.exists(video_compressed_path):
                with open(video_compressed_path, 'rb') as video:
                    await update.message.reply_video(video, caption=f"Here is your compressed video: {video_title}")
                os.remove(video_compressed_path)  # Remove the compressed file after sending
        else:
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video, caption=f"Here is your video: {video_title}")

        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text("Error: Unable to download the video. The URL may not be supported.")

# Main function to run the bot
def main() -> None:
    # Create the bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Register commands and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot with polling
    application.run_polling()

if __name__ == '__main__':
    main()
