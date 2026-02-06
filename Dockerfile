
# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory to root first to install requirements
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

# CHANGE WORKDIR TO DJANGO PROJECT ROOT
WORKDIR /app/skilllink

# Expose port 8000
EXPOSE 8000

# Start daphne
CMD daphne -b 0.0.0.0 -p ${PORT:-8000} skilllink.asgi:application
