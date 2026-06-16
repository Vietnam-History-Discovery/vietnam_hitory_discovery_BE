FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY services/ai-service/requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

RUN pip install --no-cache-dir torch==2.3.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu

COPY services/ai-service/app ./app
COPY src ./src

ENV PYTHONPATH="/app/src:/app/src/graph:/app/src/parsers:/app/src/crawlers"
ENV PROJECT_ROOT="/app"

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]