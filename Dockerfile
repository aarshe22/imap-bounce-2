FROM python:3.12-slim

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -ms /bin/bash appuser

# Set workdir
WORKDIR /app

# Copy requirements
COPY app/requirements.txt /app/requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app source and config
COPY app/ /app/
COPY data/.env.example /data/.env.example
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make data dir writable
RUN mkdir -p /data && chown -R appuser:appuser /data

# Switch to non-root user
USER appuser

# Expose web UI port
EXPOSE 8888

# Run supervisord (manages cron + uvicorn)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]