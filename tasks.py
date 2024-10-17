import yt_dlp
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_video(url):
    ydl_opts = {
        'format': 'best',  # Download the best quality video
        'outtmpl': 'downloads/%(title)s.%(ext)s',  # Path where downloaded video will be saved
        'quiet': False,  # Enable detailed logging
        'noplaylist': True,  # Ensure it doesn't download playlists
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Convert to mp4 after downloading
        }],
        'ffmpeg_location': '/bin/ffmpeg',  # Path to FFmpeg
    }

    # Ensure 'downloads' directory exists
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Attempting to download video from: {url}")
            info_dict = ydl.extract_info(url, download=True)  # Download the video
            logger.info(f"Download completed: {info_dict['title']}")
            video_file_path = os.path.join('downloads', f"{info_dict['title']}.{info_dict['ext']}")
            logger.info(f"Video saved at: {video_file_path}")
            return video_file_path

    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Example of how to use the function
def handle_video_download(url, chat_id):
    video_path = download_video(url)
    if video_path:
        logger.info(f"Successfully downloaded the video. Path: {video_path}")
        # Send the video or video path to the Telegram bot user (implement Telegram API send)
        # send_video_to_user(chat_id, video_path)
        return video_path
    else:
        logger.error(f"Failed to download video for URL: {url}")
        return None