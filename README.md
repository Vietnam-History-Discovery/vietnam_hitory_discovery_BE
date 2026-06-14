# Vietnamese History GraphRAG — Backend
A GraphRAG system applied to Vietnamese history using the Đại Việt Sử Ký Toàn Thư (DVSKTT) corpus.
## Architecture
API Gateway (Spring Boot :8080)
├── User Service (Spring Boot :8081) — Auth + JWT + PostgreSQL
├── Chat Service (Spring Boot :8082) — Chat history + PostgreSQL
└── AI Service (FastAPI :8001) — GraphRAG + Neo4j + Vector Search
## Tech Stack
| Layer | Technology |
|-------|-----------|
| API Gateway | Spring Boot 3, Spring Cloud Gateway |
| Auth | Spring Security, JWT |
| Chat | Spring Boot 3, JPA, WebClient |
| AI/RAG | FastAPI, sentence-transformers, Neo4j |
| Database | PostgreSQL (Supabase), Neo4j AuraDB |
| LLM | Groq (Llama 3.3 70B) |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 |
## Data Pipeline
PDF/Wikisource → Crawl → Parse & Chunk → NER → Knowledge Graph → Embeddings
- **Corpus**: Đại Việt Sử Ký Toàn Thư (1,504 pages, ~527K words)
- **Chunks**: 3,442 text chunks
- **Graph**: 3,600+ nodes, 1,500+ relationships
## Prerequisites
- Python 3.11+
- Java 21+
- Maven 3.9+
- Neo4j AuraDB account (free)
- Supabase account (free)
- Groq API key (free)
## Setup
**1. Clone & install Python deps**
```bash
git clone https://github.com/YOUR-ORG/graphrag-backend.git
cd graphrag-backend
pip install -r requirements.txt
```
**2. Configure environment**
```bash
cp .env.example .env
# Fill in your credentials in .env
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
python -m uvicorn app.main:app --port 8001 --reload

# Spring Boot services (each in separate terminal)
cd services/user-service && mvn spring-boot:run
cd services/api-gateway && mvn spring-boot:run
cd services/chat-service && mvn spring-boot:run
```
## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Login → JWT |
| POST | `/api/chat/sessions` | Create chat session |
| POST | `/api/chat/sessions/{id}/ask` | Ask question |
| GET | `/api/dynasties` | List dynasties |
| GET | `/api/dynasties/{name}` | Dynasty detail |
| POST | `/api/ai/query` | GraphRAG query |
## Project Structure
├── src/
│   ├── crawlers/       # Data collection
│   ├── parsers/        # Text processing + NER
│   └── graph/          # GraphRAG pipeline
├── services/
│   ├── ai-service/     # FastAPI
│   ├── user-service/   # Spring Boot
│   ├── api-gateway/    # Spring Boot
│   └── chat-service/   # Spring Boot
└── data/               # Not included in repo

