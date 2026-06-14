FROM python:3.11-slim

# System deps for lxml / underthesea
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cached unless requirements change)
COPY services/ai-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared source code
COPY src/ ./src/

# Copy service code
COPY services/ai-service/ ./services/ai-service/

# data/ is large (embeddings, chunks) – mount it as a volume at runtime:
#   docker run -v $(pwd)/data:/app/data ...
# or bind in docker-compose with: volumes: - ./data:/app/data
VOLUME ["/app/data"]

EXPOSE 8001

WORKDIR /app/services/ai-service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
