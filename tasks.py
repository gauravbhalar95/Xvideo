# tasks.py

import yt_dlp
import re
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Sanitize file name
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '', filename)

# Function to download the video using yt_dlp
def download_video(url):
    ydl_opts = {
        'format': 'best[filesize<=50M]',  # Limit the video size to 50 MB
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',  # Convert to mp4 format
        }],
        'ffmpeg_location': '/bin/ffmpeg',  # Ensure ffmpeg is installed
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = sanitize_filename(info_dict['title'])
            return os.path.join('downloads', f"{title}.{info_dict['ext']}")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Background job for downloading videos
def background_download(url, chat_id):
    video_path = download_video(url)
    return chat_id, video_path
