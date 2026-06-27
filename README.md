# Vietnamese History GraphRAG

A GraphRAG (Graph Retrieval-Augmented Generation) system applied to Vietnamese history using the Đại Việt Sử Ký Toàn Thư (DVSKTT) corpus — built as a Research-Based Learning project at FPT University HCMC.

🌐 **Live Demo**: [https://vietnam-history-frontend.onrender.com](https://vietnam-history-frontend.onrender.com)

---

## Overview

This system allows users to ask questions about Vietnamese history and receive answers grounded in the DVSKTT — one of the most comprehensive chronicles of Vietnamese history. The pipeline combines vector search over text chunks with graph traversal over a Neo4j knowledge graph, enabling more contextually rich answers than naive RAG approaches.

---

## Architecture

```
Frontend (React/Vite)
        │
        ▼
API Gateway :8080 (Spring Cloud Gateway + JWT)
        │
        ├──▶ User Service :8081   (Profile + Firestore)
        ├──▶ Chat Service :8082   (Chat history + Firestore)
        └──▶ AI Service   :8001   (GraphRAG pipeline)
                │
                ├──▶ Neo4j AuraDB      (Knowledge Graph)
                ├──▶ HuggingFace       (Embeddings cache)
                └──▶ OpenAI GPT-4o-mini (LLM generation)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, TailwindCSS |
| API Gateway | Spring Boot 3, Spring Cloud Gateway |
| Auth | Spring Security, JWT |
| Chat | Spring Boot 3, JPA, WebClient |
| AI/RAG | FastAPI, sentence-transformers, rank-bm25 |
| Graph DB | Neo4j AuraDB |
| Relational DB | PostgreSQL (Supabase) |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 |
| NLP | underthesea (Vietnamese word segmentation) |
| Containerization | Docker, Docker Compose |

---

## GraphRAG Pipeline

```
PDF/Wikisource → Crawl → Parse & Chunk → NER → Knowledge Graph → Embeddings
```

**Corpus stats:**
- Source: Đại Việt Sử Ký Toàn Thư (1,504 pages, ~527K words)
- Chunks: 3,442 text chunks
- Knowledge Graph: 3,615 nodes, 3,512 relationships

**Retrieval flow:**
1. **Entity extraction** — detect named entities from query
2. **Hybrid search** — BM25 + vector search fused via Reciprocal Rank Fusion (RRF)
3. **Graph expansion** — traverse Neo4j to find related entities and neighbor chunks
4. **Context assembly** — merge entity info, chunks, and graph relationships
5. **LLM generation** — GPT-4o-mini generates answer grounded in context

---

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Render | https://vietnam-history-frontend.onrender.com |
| API Gateway | Render | https://vietnam-history-api-gateway.onrender.com |
| User Service | Render | https://vietnam-history-user-service.onrender.com |
| Chat Service | Render | https://vietnam-history-chat-service.onrender.com |
| AI Service | HuggingFace Spaces | https://nguynanhkhoa-vietnam-history-ai-service.hf.space |

---

## Quick Start (Docker)

```bash
git clone https://github.com/Vietnam-History-Discovery/vietnam_hitory_discovery_BE
cd vietnam_hitory_discovery_BE

cp .env.example .env
# Fill in your credentials in .env

docker-compose up -d
```

All services start automatically. Frontend available at `http://localhost:3000`.

---

## Manual Setup

**Prerequisites:**
- Python 3.11+
- Java 21+
- Maven 3.9+
- Neo4j AuraDB account (free tier available)
- Supabase account (free tier available)
- OpenAI API key

**1. Clone & install Python deps**
```bash
git clone https://github.com/Vietnam-History-Discovery/vietnam_hitory_discovery_BE
cd vietnam_hitory_discovery_BE
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Fill in your credentials
```

**3. Run data pipeline**
```bash
python src/crawlers/pdf_extractor.py --pdf data/raw/dvsktt.pdf --start-page 20
python src/parsers/text_cleaner.py
python src/parsers/ner_extractor.py
python src/graph/graph_builder.py
```

**4. Start services**
```bash
# AI Service
cd services/ai-service
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload

# Spring Boot services (each in separate terminal)
cd services/user-service && mvn spring-boot:run
cd services/api-gateway && mvn spring-boot:run
cd services/chat-service && mvn spring-boot:run
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login → JWT token |
| POST | `/api/chat/sessions` | Create chat session |
| GET | `/api/chat/sessions` | List chat sessions |
| POST | `/api/chat/sessions/{id}/ask` | Ask a question |
| GET | `/api/dynasties` | List all dynasties |
| GET | `/api/dynasties/{name}` | Dynasty detail |
| POST | `/api/ai/query` | Direct GraphRAG query |
| GET | `/api/ai/health` | AI service health check |

---

## Environment Variables

```env
# Neo4j
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# OpenAI
OPENAI_API_KEY=sk-...

# Groq (optional fallback)
GROQ_API_KEY=gsk_...

# Databases
USER_DB_URL=postgresql://...
CHAT_DB_URL=postgresql://...

# Auth
JWT_SECRET=...

# Service URLs (production)
USER_SERVICE_URL=https://vietnam-history-user-service.onrender.com
CHAT_SERVICE_URL=https://vietnam-history-chat-service.onrender.com
AI_SERVICE_URL=https://nguynanhkhoa-vietnam-history-ai-service.hf.space

# CORS
CORS_ALLOWED_ORIGINS=https://vietnam-history-frontend.onrender.com
```

---

## Project Structure

```
├── src/
│   ├── crawlers/           # PDF extraction, web crawling
│   ├── parsers/            # Text cleaning, chunking, NER
│   └── graph/              # GraphRAG pipeline, embeddings
├── services/
│   ├── ai-service/         # FastAPI + GraphRAG
│   ├── user-service/       # Spring Boot auth
│   ├── api-gateway/        # Spring Cloud Gateway
│   └── chat-service/       # Spring Boot chat
├── data/                   # Not included in repo (see .gitignore)
│   ├── raw/                # Original PDF/text
│   ├── parsed/             # Processed chunks
│   └── embeddings/         # Vector cache
├── docker-compose.yml
└── .env.example
```

---

## Related Repositories

- **Frontend**: [vietnam_hitory_discovery_FE](https://github.com/Vietnam-History-Discovery/vietnam_hitory_discovery_FE)
- **AI Service (HuggingFace)**: [vietnam-history-ai-service](https://huggingface.co/spaces/nguynanhkhoa/vietnam-history-ai-service)
