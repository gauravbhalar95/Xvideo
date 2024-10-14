# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    wget \
    build-essential \
    libass-dev \
    libmp3lame-dev \
    libopus-dev \
    libtheora-dev \
    libvorbis-dev \
    libx264-dev \
    libx265-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on (if applicable)
EXPOSE 8000  # Change this to the port your app uses

# Command to run the application
CMD ["python", "app.py"]  # Replace 'your_script.py' with the main script of your application
