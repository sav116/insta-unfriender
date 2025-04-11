FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Pillow requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs and settings directories
RUN mkdir -p logs settings

# Create settings directory for persistent session storage
RUN mkdir -p /app/settings
VOLUME ["/app/settings"]

# Run as non-root user for better security
RUN useradd -m botuser
RUN chown -R botuser:botuser /app
USER botuser

# Command to run the application
CMD ["python", "main.py"] 