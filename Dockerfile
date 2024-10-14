# Use a lightweight official Python image.
FROM python:3.9-slim

# Set environment variables to avoid Python buffering output and writing .pyc files.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container.
WORKDIR /app

# Copy the local application code to the container.
COPY . /app/

# Install the required Python packages.
RUN pip install --no-cache-dir -r requirements.txt

# Expose ports for both the bot and health check
EXPOSE 8000 8001

# Command to run the application.
CMD python3 app.py
