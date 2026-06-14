"""
Phase 4 — GraphRAG Retriever
Pipeline: Embed → Vector Search → Graph Expansion → Claude Generate

Không cần Qdrant server riêng — dùng in-memory vector store
để đơn giản hoá setup cho research.
"""

import json
import os
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY")

PARSED_DIR = os.path.join(os.path.dirname(__file__), "../../data/parsed")
EMBED_DIR  = os.path.join(os.path.dirname(__file__), "../../data/embeddings")

# Model đa ngôn ngữ, hỗ trợ tiếng Việt tốt
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K       = 5   # số chunks lấy từ vector search
HOP         = 2   # số bước traverse graph


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class RetrievedContext:
    chunks:        list[dict]         # chunks từ vector search
    entities:      list[str]          # entities extracted từ chunks
    graph_context: list[dict]         # nodes/rels từ graph traversal
    query:         str


# ─── Step 1: Embeddings ───────────────────────────────────────────────────────

class EmbeddingStore:
    """
    In-memory vector store — lưu embeddings vào file .npy để tránh
    re-embed mỗi lần chạy.
    """

    def __init__(self, model_name: str = EMBED_MODEL):
        print(f"🔤 Load embedding model: {model_name}")
        from sentence_transformers import SentenceTransformer
        self.model   = SentenceTransformer(model_name)
        self.chunks  : list[dict]       = []
        self.vectors : Optional[np.ndarray] = None
        os.makedirs(EMBED_DIR, exist_ok=True)

    def build(self, chunks_path: Optional[str] = None):
        """Embed tất cả chunks, lưu cache."""
        if chunks_path is None:
            chunks_path = os.path.join(PARSED_DIR, "dvsktt_chunks.json")

        vec_path   = os.path.join(EMBED_DIR, "dvsktt_vectors.npy")
        chunk_path = os.path.join(EMBED_DIR, "dvsktt_chunks_cache.json")

        # Load cache nếu đã có
        if os.path.exists(vec_path) and os.path.exists(chunk_path):
            print("📦 Load embeddings từ cache...")
            self.vectors = np.load(vec_path)
            with open(chunk_path, encoding="utf-8") as f:
                self.chunks = json.load(f)
            print(f"   {len(self.chunks)} chunks loaded\n")
            return

        # Build mới
        print(f"⚙️  Embedding chunks từ {chunks_path}...")
        with open(chunks_path, encoding="utf-8") as f:
            self.chunks = json.load(f)

        texts = [c["text"] for c in self.chunks]
        print(f"   Encoding {len(texts)} chunks...")
        self.vectors = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

        # Lưu cache
        np.save(vec_path, self.vectors)
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False)
        print(f"💾 Saved embeddings → {vec_path}\n")

    def search(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Cosine similarity search."""
        q_vec = self.model.encode([query], normalize_embeddings=True)[0]
        scores = (self.vectors @ q_vec)  # dot product = cosine vì đã normalize
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_idx:
            chunk = self.chunks[idx].copy()
            chunk["score"] = float(scores[idx])
            results.append(chunk)
        return results


# ─── Step 2: Graph Expansion ──────────────────────────────────────────────────

class GraphExpander:
    """
    Từ danh sách chunk_ids → tìm entities → traverse graph
    để lấy thêm context liên quan.
    """

    def __init__(self):
        from neo4j import GraphDatabase
        if not NEO4J_URI:
            raise ValueError("Thiếu NEO4J_URI trong .env")
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def _run(self, query: str, **params):
        with self.driver.session() as s:
            return s.run(query, **params).data()

    def get_entities_from_chunks(self, chunk_ids: list[str]) -> list[str]:
        """Lấy tất cả entities được nhắc đến trong các chunks."""
        rows = self._run("""
            MATCH (e)-[:MENTIONED_IN]->(c:Chunk)
            WHERE c.chunk_id IN $chunk_ids
            RETURN DISTINCT coalesce(e.name, e.text) AS entity,
                            labels(e)[0] AS type
            ORDER BY type, entity
        """, chunk_ids=chunk_ids)
        return [r["entity"] for r in rows if r["entity"]]

    def expand(self, chunk_ids: list[str], hops: int = HOP) -> dict:
        """
        Graph traversal từ entities trong chunks.
        Trả về: entities, relations, neighboring chunks.
        """
        # 1. Lấy entities từ chunks
        entities = self.get_entities_from_chunks(chunk_ids)
        if not entities:
            return {"entities": [], "relations": [], "neighbor_chunks": []}

        # 2. Lấy relations giữa các entities (semantic + co-occurrence)
        relations = self._run("""
            MATCH (a)-[r]-(b)
            WHERE (a.name IN $entities OR a.text IN $entities)
              AND type(r) <> 'MENTIONED_IN'
            RETURN coalesce(a.name, a.text) AS from,
                   type(r)                  AS rel,
                   coalesce(b.name, b.text) AS to,
                   r.count                  AS weight
            ORDER BY weight DESC
            LIMIT 30
        """, entities=entities)

        # 3. Lấy neighboring chunks (chunks khác cũng nhắc đến entities này)
        neighbor_chunks = self._run("""
            MATCH (e)-[:MENTIONED_IN]->(c:Chunk)
            WHERE (e.name IN $entities OR e.text IN $entities)
              AND NOT c.chunk_id IN $chunk_ids
            RETURN DISTINCT c.chunk_id AS chunk_id,
                            c.title    AS title,
                            c.text     AS text
            LIMIT 5
        """, entities=entities, chunk_ids=chunk_ids)

        return {
            "entities":        entities,
            "relations":       relations,
            "neighbor_chunks": neighbor_chunks,
        }


# ─── Step 3: Context Builder ──────────────────────────────────────────────────

def build_context(query: str, vector_chunks: list[dict], graph_data: dict) -> str:
    """
    Gom tất cả context thành 1 string để đưa vào LLM.
    Format rõ ràng để Claude dễ tham chiếu.
    """
    parts = []

    # A. Chunks từ vector search
    parts.append("## Đoạn văn liên quan từ Đại Việt Sử Ký Toàn Thư\n")
    for i, chunk in enumerate(vector_chunks, 1):
        parts.append(f"[{i}] {chunk['title']} (score: {chunk['score']:.2f})")
        parts.append(chunk["text"])
        parts.append("")

    # B. Entities tìm được
    if graph_data["entities"]:
        parts.append("## Nhân vật / Địa danh / Sự kiện liên quan\n")
        parts.append(", ".join(graph_data["entities"]))
        parts.append("")

    # C. Quan hệ từ graph
    if graph_data["relations"]:
        parts.append("## Quan hệ trong Knowledge Graph\n")
        for r in graph_data["relations"][:15]:
            weight = f" (x{r['weight']})" if r.get("weight") else ""
            parts.append(f"• {r['from']} —[{r['rel']}]→ {r['to']}{weight}")
        parts.append("")

    # D. Chunks bổ sung từ graph traversal
    if graph_data["neighbor_chunks"]:
        parts.append("## Đoạn văn bổ sung (từ graph traversal)\n")
        for chunk in graph_data["neighbor_chunks"]:
            parts.append(f"[+] {chunk['title']}")
            parts.append(chunk["text"][:300] + "...")
            parts.append("")

    return "\n".join(parts)


# ─── Step 4: Claude Generator ─────────────────────────────────────────────────

class ClaudeGenerator:
    def __init__(self):
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Thiếu GROQ_API_KEY trong .env")
        self.client = Groq(api_key=api_key)

    def generate(self, query: str, context: str) -> str:
        prompt = f"""Bạn là chuyên gia lịch sử Việt Nam. Chỉ dùng thông tin từ context sau để trả lời.
QUAN TRỌNG: Chỉ trả lời dựa trên thông tin có trong context. Nếu context không đề cập, hãy nói "Không có thông tin trong tài liệu."
Context:
{context}

Câu hỏi: {query}

Trả lời bằng tiếng Việt, súc tích và chính xác:"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        return response.choices[0].message.content


# ─── Main GraphRAG Pipeline ───────────────────────────────────────────────────

class GraphRAG:
    def __init__(self):
        self.embed_store = EmbeddingStore()
        self.embed_store.build()
        self.expander    = GraphExpander()
        self.generator   = ClaudeGenerator()
        print("✅ GraphRAG ready\n")

    def query(self, question: str, verbose: bool = True) -> str:
        if verbose:
            print(f"❓ Query: {question}\n")

        # Step 1: Vector search
        vector_chunks = self.embed_store.search(question, top_k=TOP_K)
        chunk_ids = [c["chunk_id"] for c in vector_chunks]
        if verbose:
            print(f"🔍 Vector search → {len(vector_chunks)} chunks:")
            for c in vector_chunks:
                print(f"   [{c['score']:.3f}] {c['title']}")

        # Step 2: Graph expansion
        graph_data = self.expander.expand(chunk_ids)
        if verbose:
            print(f"\n🕸️  Graph expansion:")
            print(f"   Entities    : {len(graph_data['entities'])}")
            print(f"   Relations   : {len(graph_data['relations'])}")
            print(f"   Extra chunks: {len(graph_data['neighbor_chunks'])}")

        # Step 3: Build context
        context = build_context(question, vector_chunks, graph_data)

        # Step 4: Generate
        if verbose:
            print(f"\n🤖 Generating answer...\n")
        answer = self.generator.generate(question, context)

        return answer

    def close(self):
        self.expander.close()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rag = GraphRAG()

    # Test queries
    test_questions = [
        "Triệu Đà là ai và ông ta lập nước Nam Việt như thế nào?",
        "Hai Bà Trưng khởi nghĩa chống lại ai và kết quả như thế nào?",
        "Nước Văn Lang được thành lập như thế nào?",
    ]

    try:
        for q in test_questions:
            print("=" * 60)
            answer = rag.query(q)
            print(f"\n📝 Trả lời:\n{answer}\n")
    finally:
        rag.close()