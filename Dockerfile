
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
# RUN python manage.py collectstatic --noinput

# Make the start script executable (if we were using one, but we'll use CMD for simplicity or fly.toml release command)
# RUN chmod +x /app/build.sh

# Expose port 8000
EXPOSE 8000

# Start daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "skilllink.asgi:application"]
