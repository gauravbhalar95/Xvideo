# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script into the container
COPY bot.py .

# Create a downloads directory
RUN mkdir downloads

# Command to run the bot
CMD ["python", "bot.py"]
