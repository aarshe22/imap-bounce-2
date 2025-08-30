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
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic
ADD https://github.com/aptible/supercronic/releases/download/v0.2.2/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

# Create app user
RUN useradd -ms /bin/bash appuser

WORKDIR /app

# Copy requirements first for caching
COPY app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copy source code + config
COPY app/ /app/
COPY data/.env.example /data/.env.example
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY crontab /app/crontab

# Fix permissions
RUN chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8888
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]