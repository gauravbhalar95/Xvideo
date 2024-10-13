import os
import subprocess
import logging
import yt_dlp as youtube_dl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import nest_asyncio
import shutil
from tqdm import tqdm

# Apply the patch for nested event loops
nest_asyncio.apply()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the static ffmpeg binary
FFMPEG_PATH = '/bin/ffmpeg'  # Update this path based on your environment

# Telegram bot setup
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError("Error: BOT_TOKEN is not set")

# Create downloads directory if it doesn't exist
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Store download history
download_history = []

# Function to download video using yt-dlp
def download_video(url, format='best'):
    ydl_opts = {
        'format': format,
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': False,
        'ffmpeg_location': FFMPEG_PATH,  # Specify local ffmpeg binary
        'retries': 3,
        'continuedl': True,
        'noplaylist': True,
        'progress_hooks': [hook],  # Add progress hook
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict and 'title' in info_dict:
                file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
                logger.info(f"Video downloaded to: {file_path}")  # Debugging output
                return file_path, info_dict['title'], info_dict['ext']
            else:
                logger.error("Error: No information retrieved from the video URL.")
                return None, None, None
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None, None, None

# Hook to display download progress
def hook(d):
    if d['status'] == 'downloading':
        total_bytes = d['total_bytes']
        downloaded_bytes = d['downloaded_bytes']
        progress = (downloaded_bytes / total_bytes) * 100
        logger.info(f"Download progress: {progress:.2f}%")

# Function to compress video using ffmpeg
def compress_video(input_path):
    video_title = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join('downloads', f"compressed_{video_title}.mp4")
    command = [FFMPEG_PATH, '-i', input_path, '-vcodec', 'libx264', '-crf', '23', output_path]

    try:
        subprocess.run(command, check=True)
        logger.info(f"Video compressed to: {output_path}")  # Debugging output
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during compression: {e}")
        return None

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
        logger.info(f"Downloaded video path: {video_path}")  # Debugging output
        file_size = os.path.getsize(video_path)  # Get file size in bytes
        logger.info(f"File size: {file_size} bytes")  # Debugging output

        # Check if the file is larger than 2GB
        if file_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
            await update.message.reply_text(f"The video is larger than 2GB ({file_size / (1024 * 1024):.2f}MB).")
        elif file_size > 100 * 1024 * 1024:  # 100MB limit
            await update.message.reply_text(f"The video is larger than 100MB ({file_size / (1024 * 1024):.2f}MB). Compressing it...")

            # Compress the video
            video_compressed_path = compress_video(video_path)

            # Check if compression was successful
            if video_compressed_path and os.path.exists(video_compressed_path):
                with open(video_compressed_path, 'rb') as video:
                    await update.message.reply_video(video, caption=f"Here is your compressed video: {video_title}")
                os.remove(video_compressed_path)  # Remove the compressed file after sending
            else:
                await update.message.reply_text("Error: Compression failed. Please try again later.")
        else:
            await update.message.reply_text(f"The video size is acceptable ({file_size / (1024 * 1024):.2f}MB). Sending it...")
            with open(video_path, 'rb') as video:
                await update.message.reply_video(video, caption=f"Here is your video: {video_title}")

        # Add to download history
        download_history.append((video_title, video_path))

        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text("Error: Unable to download the video. The URL may not be supported or invalid.")

# Adding format and quality selection
async def format_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Best (default)", callback_data='best')],
        [InlineKeyboardButton("MP4", callback_data='mp4')],
        [InlineKeyboardButton("MKV", callback_data='mkv')],
        [InlineKeyboardButton("720p", callback_data='720p')],
        [InlineKeyboardButton("1080p", callback_data='1080p')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select the format and quality:", reply_markup=reply_markup)

# Handle user's selection for format and quality
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    selected_option = query.data

    # Store the selected option in context
    context.user_data['selected_format'] = selected_option

    # Prompt user to send the video URL again after selecting format
    await query.edit_message_text(text=f"Selected format: {selected_option}. Now, please send the video URL.")

# Command to trigger format selection
async def request_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await format_selection(update, context)

# Command to show download history
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if download_history:
        history_message = "Download History:\n"
        for title, path in download_history:
            history_message += f"- {title}\n"
        await update.message.reply_text(history_message)
    else:
        await update.message.reply_text("No download history available.")

# Command to display help information
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Usage:\n"
        "/start - Start the bot\n"
        "/select_format - Select the format and quality\n"
        "/history - View your download history\n"
        "Simply send a video URL to download the video."
    )
    await update.message.reply_text(help_text)

# Main function to run the bot
def main() -> None:
    # Create the bot application
    application = ApplicationBuilder().token(TOKEN).build()

    # Register commands and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("select_format", request_video_url))  # New command for format selection
    application.add_handler(CommandHandler("history", show_history))  # Command for download history
    application.add_handler(CommandHandler("help", help_command))  # Help command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))  # Register button handler for format selection

    # Start the bot with polling
    application.run_polling()

if __name__ == '__main__':
    main()
