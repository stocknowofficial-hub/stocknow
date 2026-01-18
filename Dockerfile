# Base Image
FROM python:3.11-slim

# Working Directory
WORKDIR /app

# Install system dependencies (for building some python packages if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Project Code
COPY . .

# Set Python Path
ENV PYTHONPATH=/app

# Default Command (Overridden in docker-compose)
CMD ["python", "app.py"]
