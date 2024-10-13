# Base image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port for health checks (optional)
EXPOSE 8000

# Set environment variables
ENV BOT_TOKEN=your-telegram-bot-token-here

# Run the application
CMD ["python", "app.py"]
