# Use an official Python runtime as a base image
FROM python:3.10-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set environment variables for Flask and bot tokens
ENV BOT_TOKEN=7232982155:AAFDc1SGZ3T8ZUiOun4oEbPpQpr3-6zKuAM \
    WEBHOOK_URL=https://everyday-nessie-telegramboth-1ba5f30e.koyeb.app/

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container
COPY . .

# Install any needed packages specified in requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Make the directories for downloads (videos)
RUN mkdir -p downloads

# Expose the port that Flask will run on
EXPOSE 5000

# Expose the health check app port
EXPOSE 8000

# Command to run both the health check app and the bot application
CMD ["python3", "-m", "webhook"]
