import os
import yt_dlp as youtube_dl
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nest_asyncio
import logging
import requests
from bs4 import BeautifulSoup
from moviepy.editor import VideoFileClip

# Apply the patch for nested event loops
nest_asyncio.apply()

# Enable logging for debugging
logging.basicConfig(level=logging.INFO)

# Bot token (replace with your actual token)
TOKEN = os.getenv("BOT_TOKEN")

# Function to download video using yt-dlp
def download_video(url, platform):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': f'downloads/%(title)s_{platform}.%(ext)s',
        'quiet': False,
        'retries': 5,
        'continuedl': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
    }

    # Create downloads directory if it doesn't exist
    os.makedirs('downloads', exist_ok=True)

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            if info_dict and 'title' in info_dict:
                file_path = os.path.join('downloads', f"{info_dict['title']}_{platform}.mp4")
                return file_path, info_dict['title']
            else:
                return None, None
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None, None

# Scraping function for fetching the video URL (example for XHamster and Xvideos)
def fetch_video_url_from_page(page_url):
    try:
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Example for XHamster (adjust the selectors for each site)
        video_url = soup.find('video')['src'] if soup.find('video') else None
        return video_url
    except Exception as e:
        print(f"Error fetching video URL: {e}")
        return None

# Function to process video (compress, trim, or resize)
def process_video(video_path):
    try:
        clip = VideoFileClip(video_path)
        # Check if video is too large (over 2GB), trim or resize it
        max_duration = 10 * 60  # 10 minutes as an example for trimming
        if clip.duration > max_duration:
            clip = clip.subclip(0, max_duration)

        # Resize if needed (example: resize to 720p)
        if clip.size[1] > 720:  # if height > 720 pixels
            clip = clip.resize(height=720)

        # Save the processed video
        output_path = video_path.replace(".mp4", "_processed.mp4")
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        return output_path
    except Exception as e:
        print(f"Error processing video: {e}")
        return None

# Command /start to welcome the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome! Send me a video link to download from YouTube, XHamster, Xvideos, or any other supported platform.")

# Handle messages with URLs
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    if 'youtube.com' in url or 'youtu.be' in url:
        platform = "YouTube"
    elif 'xvideos.com' in url:
        platform = "Xvideos"
    elif 'xhamster.com' in url:
        platform = "XHamster"
        # Fetch the actual video URL from the page
        url = fetch_video_url_from_page(url)
        if not url:
            await update.message.reply_text("Error fetching the video URL from the page.")
            return
    else:
        await update.message.reply_text("This URL is not supported.")
        return

    await update.message.reply_text(f"Downloading video from {platform}...")

    # Download the video
    video_path, video_title = download_video(url, platform)

    if video_path and os.path.exists(video_path):
        await update.message.reply_text(f"Processing video: {video_title}...")
        
        # Process the video using moviepy (trim, resize)
        processed_video_path = process_video(video_path)

        if processed_video_path and os.path.exists(processed_video_path):
            with open(processed_video_path, 'rb') as video:
                await update.message.reply_video(video, caption=f"Here is your processed video: {video_title}")
            os.remove(processed_video_path)  # Clean up the processed video
        else:
            await update.message.reply_text("Error processing the video.")
        
        os.remove(video_path)  # Clean up the original video
    else:
        await update.message.reply_text("Error downloading the video. Please try again.")

# Main function to run the bot
def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    # Command handler for /start
    application.add_handler(CommandHandler("start", start))

    # Message handler for URLs
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()