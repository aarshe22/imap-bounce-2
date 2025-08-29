FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
RUN apt-get update && apt-get install -y cron openssl && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /certs && \
    openssl req -x509 -nodes -newkey rsa:2048 \
      -subj "/CN=localhost" \
      -keyout /certs/selfsigned.key \
      -out /certs/selfsigned.crt \
      -days 365
RUN echo "*/5 * * * * python /app/process_bounces.py >> /data/cron.log 2>&1" >> /etc/cron.d/bounce \
 && echo "*/15 * * * * python /app/retry_queue.py >> /data/cron.log 2>&1" >> /etc/cron.d/bounce \
 && echo "0 0 * * * python /app/daily_summary.py >> /data/cron.log 2>&1" >> /etc/cron.d/bounce \
 && chmod 0644 /etc/cron.d/bounce
CMD service cron start && \
    CERT_KEY=${SSL_KEY:-/certs/selfsigned.key} && \
    CERT_CRT=${SSL_CRT:-/certs/selfsigned.crt} && \
    uvicorn webui:app --host 0.0.0.0 --port ${WEBUI_HTTPS_PORT} \
        --ssl-keyfile $CERT_KEY --ssl-certfile $CERT_CRT
