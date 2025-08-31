FROM python:3.12-slim

# Install required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libpq-dev \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic for cron-like scheduling
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.30/supercronic-linux-amd64
RUN curl -fsSL "$SUPERCRONIC_URL" -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

# Set up app directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application source
COPY . /app/

# Create non-root user
RUN useradd -m appuser && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser

# Expose the web dashboard port
EXPOSE 8888

# Command: run supercronic + uvicorn together
# supercronic runs cron schedule defined in /app/crontab
# uvicorn runs the FastAPI web dashboard
CMD ["/bin/sh", "-c", "supercronic /app/crontab & uvicorn webui:app --host 0.0.0.0 --port 8888"]