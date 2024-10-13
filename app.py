import os
import yt_dlp as youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio

# Apply the patch for nested event loops
nest_asyncio.apply()

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
        'retries': 3,
        'continuedl': True,
        'noplaylist': True,
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict and 'title' in info_dict:
                file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
                print(f"Video downloaded to: {file_path}")  # Debugging output
                return file_path, info_dict['title'], info_dict['ext']
            else:
                print("Error: No information retrieved from the video URL.")
                return None, None, None
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None, None, None

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
        print(f"Downloaded video path: {video_path}")  # Debugging output
        file_size = os.path.getsize(video_path)  # Get file size in bytes
        print(f"File size: {file_size} bytes")  # Debugging output

        # Check if the file size is acceptable (less than 2GB)
        if file_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
            await update.message.reply_text(f"The video is larger than 2GB ({file_size / (1024 * 1024 * 1024):.2f}GB).")
        else:
            await update.message.reply_text(f"The video size is acceptable ({file_size / (1024 * 1024 * 1024):.2f}GB). Sending it...")

            try:
                with open(video_path, 'rb') as video:
                    await update.message.reply_video(video, caption=f"Here is your video: {video_title}")
            except Exception as e:
                await update.message.reply_text(f"Error sending video: {str(e)}")
                print(f"Error: {e}")  # Debugging: print error message

        os.remove(video_path)  # Remove the file after sending
    else:
        await update.message.reply_text("Error: Unable to download the video. The URL may not be supported or invalid.")

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
