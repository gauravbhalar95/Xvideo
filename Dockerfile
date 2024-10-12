# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to the working directory
COPY . .

# Download FFmpeg
RUN apt-get update && \
    apt-get install -y wget && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz && \
    tar -xvf ffmpeg-release-i686-static.tar.xz && \
    mv ffmpeg-*/ffmpeg ./ffmpeg && \
    rm -rf ffmpeg-* && \
    chmod +x ./ffmpeg  # Make the ffmpeg binary executable

# Command to run your bot
CMD ["python", "main.py"]
