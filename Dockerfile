# Use official Python slim image
FROM python:3.12-slim

# Create appuser
RUN useradd -ms /bin/bash appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (lightweight cron for containers)
RUN curl -fsSLo /usr/local/bin/supercronic https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 \
    && chmod +x /usr/local/bin/supercronic

# Create working dirs
RUN mkdir -p /app /data /logs

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app source (flatten contents of app/ into /app/)
COPY app/ /app/
COPY crontab /app/crontab
COPY supervisord.conf /app/supervisord.conf
COPY docker-compose.yml /app/docker-compose.yml
COPY Makefile /app/Makefile
COPY README.md /app/README.md
COPY docs/ /app/docs/

# Ensure permissions
RUN chown -R appuser:appuser /app /data /logs

USER appuser

CMD ["supervisord", "-c", "/app/supervisord.conf"]