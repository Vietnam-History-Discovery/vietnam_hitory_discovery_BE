#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "==========================================="
echo "   AI Document Ingestion Pipeline          "
echo "==========================================="

if [ -z "$1" ]; then
  echo "Usage: ./ingest.sh <path_to_pdf_file>"
  echo "Example: ./ingest.sh data/raw/my_document.pdf"
  exit 1
fi

HOST_PDF_PATH=$1

if [ ! -f "$HOST_PDF_PATH" ]; then
  echo "❌ Error: File not found: $HOST_PDF_PATH"
  echo "Make sure the file exists relative to the current directory."
  exit 1
fi

# We assume the PDF is placed inside the data/ folder because the data/ folder is mounted to /app/data in the container.
if [[ "$HOST_PDF_PATH" != data/* ]]; then
  echo "❌ Error: The PDF must be placed inside the 'data/' directory (e.g. data/raw/doc.pdf) so the Docker container can access it."
  exit 1
fi

# Map the host path to the container path (/app/data/...)
CONTAINER_PDF_PATH="/app/${HOST_PDF_PATH}"

echo "📦 Installing pdfplumber inside ai-service container..."
docker compose exec -T ai-service bash -c "pip install pdfplumber"

echo "📖 [1/5] Extracting text from PDF: $HOST_PDF_PATH..."
docker compose exec -T ai-service bash -c "python src/crawlers/pdf_extractor.py --pdf $CONTAINER_PDF_PATH"

echo "🧹 [2/5] Cleaning and chunking text..."
docker compose exec -T ai-service bash -c "python src/parsers/text_cleaner.py"

echo "🧠 [3/5] Extracting Entities (NER)..."
docker compose exec -T ai-service bash -c "python src/parsers/ner_extractor.py"

echo "🕸️  [4/5] Building Knowledge Graph in Neo4j..."
docker compose exec -T ai-service bash -c "python src/graph/graph_builder.py"

echo "🔄 [5/5] Restarting AI Service to load new embeddings..."
docker compose restart ai-service

echo "✅ All done! The new document has been ingested and the AI is ready."
