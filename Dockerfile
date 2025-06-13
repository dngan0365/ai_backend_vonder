# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    npm \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Prisma CLI globally via npm
RUN npm install -g prisma

# Install Python dependencies (use separate layer to cache)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy only necessary files
COPY . .

# Generate Prisma client
RUN prisma generate

# (Optional) Run DB migrations on deploy
# RUN prisma migrate deploy

# Expose API port
EXPOSE 8000

# Start app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
