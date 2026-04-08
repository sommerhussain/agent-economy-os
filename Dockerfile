# Use the official Python 3.11 slim image for a small, secure base
FROM python:3.11-slim as builder

# Prevent Python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install build dependencies (if needed in the future for packages like psycopg2)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
# We simulate a requirements.txt here based on the project's known dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the application using Uvicorn
# We bind to 0.0.0.0 to allow external access (required by most PaaS providers like Render/Railway)
# Use the PORT environment variable if set, otherwise default to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
