#!/bin/bash

# Instagram Unfriender Bot - Build and Run Script

# Exit on error
set -e

# Display commands
echo "🔨 Building and running Instagram Unfriender Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your configuration based on .env.example."
    exit 1
fi

# Load variables from .env file
export $(grep -v '^#' .env | xargs)

# Check for required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN is not set in .env file."
    exit 1
fi

# Create necessary directories
mkdir -p logs settings

# Build Docker image
echo "🔄 Building Docker image..."
docker build -t insta-unfriender:latest .

# Check if the container exists (running or not)
CONTAINER_ID=$(docker ps -a -q -f name=insta-unfriender)
if [ ! -z "$CONTAINER_ID" ]; then
    echo "🔄 Stopping and removing existing container..."
    docker stop insta-unfriender 2>/dev/null || true
    docker rm insta-unfriender 2>/dev/null || true
fi

# Run the container
echo "🚀 Starting the bot..."
docker run -d --name insta-unfriender \
    --restart unless-stopped \
    --env-file .env \
    -v "$(pwd)/logs:/app/logs" \
    -v "$(pwd)/bot_data.db:/app/bot_data.db" \
    -v "$(pwd)/settings:/app/settings" \
    insta-unfriender:latest

echo "✅ Bot is running in the background!"
echo "To view logs, run: docker logs -f insta-unfriender"
echo "To check available exceptions in instagrapi, run: docker exec insta-unfriender python check_exceptions.py" 