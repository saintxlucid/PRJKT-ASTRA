# services/bridge/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY services/bridge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY services/bridge/ /app/
COPY src /app/src

# Runtime dirs
RUN mkdir -p /data /tmp/bridge_safe && \
    chown -R 1000:1000 /data /tmp/bridge_safe
USER 1000

EXPOSE 8888
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8888/health || exit 1

CMD ["uvicorn", "bridge_server:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "1"]
