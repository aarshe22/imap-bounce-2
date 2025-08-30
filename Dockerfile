FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    libmagic-dev \
    gcc \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -ms /bin/bash appuser

# Prepare directories for cron + logs
RUN mkdir -p /data /var/spool/cron/crontabs && \
    chown -R appuser:appuser /data /var/spool/cron

WORKDIR /app

COPY app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
COPY data/.env.example /data/.env.example
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set permissions
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8888
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]