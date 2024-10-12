# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and install ffmpeg
RUN apt-get update && \
    apt-get install -y wget && \
    wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz && \
    tar -xf ffmpeg-release-i686-static.tar.xz && \
    mv ffmpeg-* ffmpeg && \
    chmod +x ffmpeg/ffmpeg && \
    mv ffmpeg/ffmpeg /usr/local/bin/ffmpeg && \
    rm -rf ffmpeg-* ffmpeg-release-i686-static.tar.xz

# Copy the entire project to the working directory
COPY . .

# Command to run your bot
CMD ["python", "main.py"]
