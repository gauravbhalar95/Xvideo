# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    build-essential \
    libass-dev \
    libfdk-aac-dev \
    libmp3lame-dev \
    libopus-dev \
    libtheora-dev \
    libvorbis-dev \
    libx264-dev \
    libx265-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install FFmpeg
RUN wget https://ffmpeg.org/releases/ffmpeg-release-full.tar.bz2 && \
    tar -xjf ffmpeg-release-full.tar.bz2 && \
    cd ffmpeg-* && \
    ./configure --enable-gpl --enable-nonfree --enable-libfdk-aac --enable-libmp3lame --enable-libx264 --enable-libx265 --enable-libtheora --enable-libvorbis --enable-libopus && \
    make && \
    make install && \
    make clean && \
    cd .. && \
    rm -rf ffmpeg-release-full.tar.bz2 ffmpeg-*

# Copy your application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the command to run your app
CMD ["python", "app.py"]
