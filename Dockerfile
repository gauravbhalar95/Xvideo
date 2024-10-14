# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for unbuffered logging
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for health check and webhook
EXPOSE 8000

# Define environment variables
ENV BOT_TOKEN=7232982155:AAFDc1SGZ3T8ZUiOun4oEbPpQpr3-6zKuAM
ENV WEBHOOK_URL=https://everyday-nessie-telegramboth-1ba5f30e.koyeb.app/

# Start the bot and Flask server using the bot.py script
CMD ["python", "app.py"]
