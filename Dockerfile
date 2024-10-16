# Use the official Python image
FROM python:3.10-slim

# Set environment variables to avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg and other required system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install Python dependencies from requirements.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your application will run on
EXPOSE 8000

# Set environment variables (These can also be set in the Koyeb dashboard)
ENV BOT_TOKEN=7232982155:AAFDc1SGZ3T8ZUiOun4oEbPpQpr3-6zKuAM
ENV WEBHOOK_URL=https://everyday-nessie-telegramboth-1ba5f30e.koyeb.app/
ENV PORT=8000

# Start the bot
CMD python app.py