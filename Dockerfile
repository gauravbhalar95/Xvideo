# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies needed for yt-dlp and ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 to the outside world
EXPOSE 8080

# Set environment variables (replace with your actual environment variables)
ENV BOT_TOKEN=7232982155:AAFDc1SGZ3T8ZUiOun4oEbPpQpr3-6zKuAM
ENV WEBHOOK_URL=https://xvideo.onrender.com
ENV PORT=8080

# Command to run the bot
CMD ["python", "app.py"]
