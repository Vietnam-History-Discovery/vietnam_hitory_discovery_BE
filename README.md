# Vietnamese History GraphRAG

A GraphRAG (Graph Retrieval-Augmented Generation) system applied to Vietnamese history using the Đại Việt Sử Ký Toàn Thư (DVSKTT) corpus — built as a Research-Based Learning project at FPT University HCMC.

🌐 **Live Demo**: [https://vietnam-history-frontend.onrender.com](https://vietnam-history-frontend.onrender.com)

---

## Overview

This system allows users to ask questions about Vietnamese history and receive answers grounded in the DVSKTT — one of the most comprehensive chronicles of Vietnamese history. The pipeline combines hybrid search (BM25 + vector) over text chunks with graph traversal over a Neo4j knowledge graph, enabling more contextually rich answers than naive RAG.

**Key features:**
- 💬 **Streaming chat** — answers streamed token-by-token over SSE
- 🕰️ **Timeline mode** — generates interactive historical timelines (structured JSON) alongside a conversational answer
- 🧠 **Conversation-aware follow-ups** — sliding-window history + entity tracking, so follow-up questions like *"kết quả cuộc khởi nghĩa"* stay anchored to the entity discussed earlier (e.g. Hai Bà Trưng)
- 🏛️ **Dynasty explorer** — curated dynasty metadata with related figures, events, places, and source passages from the knowledge graph

---

## Architecture

```
Frontend (React/Vite + Firebase Auth)
        │  Bearer <Firebase ID token>
        ▼
API Gateway :8080 (Spring Cloud Gateway)
        │  verifies token via Firebase Admin SDK
        │  injects X-User-Id / X-User-Email
        │
        ├──▶ User Service :8081   (Profiles → Firestore)
        ├──▶ Chat Service :8082   (Sessions & messages → Firestore, SSE relay)
        └──▶ AI Service   :8001   (FastAPI GraphRAG pipeline)
                │
                ├──▶ Neo4j AuraDB           (Knowledge graph)
                ├──▶ In-memory vector store (sentence-transformers + BM25)
                └──▶ Groq API               (LLM generation)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, TailwindCSS |
| API Gateway | Spring Boot 3, Spring Cloud Gateway |
| Auth | Firebase Authentication (ID tokens verified by Firebase Admin SDK at the gateway) |
| User / Chat storage | Google Cloud Firestore |
| Chat Service | Spring Boot 3, SseEmitter (SSE relay to AI service) |
| AI / RAG | FastAPI, sentence-transformers, rank-bm25, underthesea |
| Graph DB | Neo4j AuraDB |
| LLM | Groq — `llama-3.3-70b-versatile` (chat), `openai/gpt-oss-120b` (timeline, configurable via `TIMELINE_MODEL`) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (cached as `.npy`, in-memory vector search) |
| Containerization | Docker, Docker Compose |

---

## GraphRAG Pipeline

```
PDF → Extract → Clean & Chunk → NER → Knowledge Graph (Neo4j) → Embeddings cache
```

**Corpus stats:**
- Source: Đại Việt Sử Ký Toàn Thư (1,504 pages, ~527K words)
- Chunks: 3,442 text chunks
- Knowledge Graph: 3,615 nodes, 3,512 relationships

**Retrieval flow (per question):**
1. **Entity extraction** — detect the named entity in the query (`extract_entity`), verified against Neo4j
2. **Conversation enrichment** — if the question has no clear entity, entities tracked from the last 6 messages of the session enrich the query (`… [context: Hai Bà Trưng]`)
3. **Hybrid search** — BM25 + vector search fused via Reciprocal Rank Fusion (RRF), optionally filtered by dynasty context
4. **Graph expansion** — traverse Neo4j from the retrieved chunks to related entities and neighbor chunks
5. **Context assembly** — entity info + chunks + graph relationships + a short sliding-window summary of recent exchanges
6. **LLM generation** — Groq generates the answer grounded in the assembled context (streamed via SSE)

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
# Place your Firebase service-account key at ./firebase.json
# (mounted read-only into the Java services)

docker-compose up -d
```

All services start automatically. Frontend available at `http://localhost:3000`, gateway at `http://localhost:8080`.

To ingest a new PDF into the running stack:

```bash
./ingest.sh data/raw/my_document.pdf
```

---

## Manual Setup

**Prerequisites:**
- Python 3.11+
- Java 21+ and Maven 3.9+
- Neo4j AuraDB account (free tier available)
- Firebase project (Authentication + Firestore) and a service-account JSON key
- Groq API key

**1. Clone & install Python deps**
```bash
git clone https://github.com/Vietnam-History-Discovery/vietnam_hitory_discovery_BE
cd vietnam_hitory_discovery_BE
pip install -r requirements.txt
```

**2. Configure environment**
```bash
cp .env.example .env
# Fill in your credentials; point GOOGLE_APPLICATION_CREDENTIALS
# at your Firebase service-account JSON (e.g. ./firebase.json)
```

**3. Run the data pipeline**
```bash
python src/crawlers/pdf_extractor.py --pdf data/raw/dvsktt.pdf --start-page 20
python src/parsers/text_cleaner.py
python src/parsers/ner_extractor.py
python src/graph/graph_builder.py
python src/graph/seed_dynasties.py          # curated Dynasty metadata
python src/graph/map_chunks_to_dynasties.py # BELONGS_TO_DYNASTY edges
```

**4. Start services**
```bash
# AI Service
cd services/ai-service
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload

# Spring Boot services (each in a separate terminal)
cd services/user-service && mvn spring-boot:run
cd services/api-gateway && mvn spring-boot:run
cd services/chat-service && mvn spring-boot:run
```

---

## API Endpoints

### Via API Gateway (`:8080`) — require `Authorization: Bearer <Firebase ID token>`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/me` | Get profile (auto-created on first call) |
| PUT | `/api/users/me` | Update username |
| POST | `/api/chat/sessions` | Create chat session (`type`: CHAT or TIMELINE) |
| GET | `/api/chat/sessions?type=` | List sessions |
| GET | `/api/chat/sessions/{id}` | Session with messages |
| DELETE | `/api/chat/sessions/{id}` | Delete session |
| POST | `/api/chat/sessions/{id}/ask` | Ask a question (JSON response) |
| POST | `/api/chat/sessions/{id}/ask/stream` | Ask a question (SSE stream) |
| POST | `/api/chat/sessions/{id}/timeline/stream` | Generate timeline (SSE: `meta → timeline → delta* → done`) |
| GET | `/api/chat/sessions/{id}/messages` | List messages |
| GET | `/api/dynasties` | List all dynasties |
| GET | `/api/dynasties/{name}` | Dynasty detail (figures, events, places, passages) |
| GET | `/api/dynasties/{name}/chat-context` | Pre-built LLM context for a dynasty |

Authentication (register/login) is handled entirely by Firebase on the frontend — there are no backend auth endpoints.

### AI Service direct (`:8001`, internal)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | GraphRAG query (accepts optional `history` for conversation context) |
| POST | `/query/stream` | Streaming GraphRAG query (SSE) |
| POST | `/query/naive` | Vector-only RAG baseline |
| POST | `/query/timeline/stream` | Timeline generation (SSE) |
| POST | `/ingest/full` | Trigger full ingestion pipeline |
| GET | `/ingest/status` | Ingestion status |
| POST | `/eval/run` | Run GraphRAG-vs-naive evaluation |
| GET | `/eval/summary` `/eval/results` | Evaluation outputs |
| GET | `/health` | Health check (Neo4j status, chunks loaded) |

---

## Environment Variables

```env
# Neo4j AuraDB
NEO4J_URI=neo4j+s://<your-auradb-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# LLM (Groq is required; others optional)
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# Firebase (backend services)
GOOGLE_APPLICATION_CREDENTIALS=/app/firebase.json

# Service URLs & CORS (API Gateway)
USER_SERVICE_URL=http://user-service:8081
CHAT_SERVICE_URL=http://chat-service:8082
AI_SERVICE_URL=http://ai-service:8001
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Firebase frontend config (build args for the frontend image)
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

See [.env.example](.env.example) for the full template.

---

## Project Structure

```
├── src/                        # Shared data pipeline (imported by ai-service)
│   ├── crawlers/               # PDF extraction
│   ├── parsers/                # Text cleaning, chunking, NER
│   └── graph/                  # Graph builder, dynasty seeding, GraphRAG retriever
├── services/
│   ├── ai-service/             # FastAPI — GraphRAG query/ingest/eval/dynasty APIs
│   ├── api-gateway/            # Spring Cloud Gateway + Firebase token verification
│   ├── chat-service/           # Spring Boot — chat sessions/messages (Firestore) + SSE relay
│   └── user-service/           # Spring Boot — user profiles (Firestore)
├── data/                       # Not included in repo (see .gitignore)
│   ├── raw/                    # Original PDF/text
│   ├── parsed/                 # Processed chunks (dvsktt_chunks.json)
│   └── embeddings/             # Vector cache (.npy)
├── firebase.json               # Firebase service-account key (not committed)
├── ingest.sh                   # Ingest a new PDF into the running Docker stack
├── docker-compose.yml
└── .env.example
```

---

## Related Repositories

- **Frontend**: [vietnam_hitory_discovery_FE](https://github.com/Vietnam-History-Discovery/vietnam_hitory_discovery_FE)
- **AI Service (HuggingFace)**: [vietnam-history-ai-service](https://huggingface.co/spaces/nguynanhkhoa/vietnam-history-ai-service)
