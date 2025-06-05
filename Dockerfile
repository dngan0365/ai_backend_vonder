# Base Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Prisma CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Install Prisma CLI globally
RUN npm install -g prisma

# Copy Python dependencies
COPY pyproject.toml poetry.lock* requirements.txt* ./

# Install Python dependencies (choose pip or poetry)
# Using pip (adjust if using poetry)
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application files
COPY . .

# Generate Prisma client
RUN prisma generate

# Run Prisma database migration (optional)
# RUN prisma migrate deploy

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
