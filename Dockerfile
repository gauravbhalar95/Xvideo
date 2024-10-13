# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y wget && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz && \
    tar -xvf ffmpeg-release-i686-static.tar.xz && \
    mv ffmpeg-*/ffmpeg /usr/local/bin/ffmpeg && \
    rm -rf ffmpeg-*

# Install any necessary system dependencies
RUN apt-get update && apt-get install -y libmagic1 && apt-get clean

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed Python packages specified in requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 8443

# Run the bot
CMD ["python", "bot.py"]
