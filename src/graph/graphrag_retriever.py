"""
Phase 4 — GraphRAG Retriever
Pipeline: Embed → Vector Search → Graph Expansion → Claude Generate

Không cần Qdrant server riêng — dùng in-memory vector store
để đơn giản hoá setup cho research.
"""

import json
import os
from groq import Groq
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from underthesea import chunk

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
TOP_K       = 10  # số chunks lấy từ vector search
HOP         = 2   # số bước traverse graph


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class RetrievedContext:
    chunks:        list[dict]         # chunks từ vector search
    entities:      list[str]          # entities extracted từ chunks
    graph_context: list[dict]         # nodes/rels từ graph traversal
    query:         str

# ─── Helpers ───────────────────────────────────────────────────────────────

import re

_BARE_ENTITY_EXCLUDES = {
    "là", "ai", "gì", "nào", "như", "thế", "bao", "nhiêu",
    "đâu", "khi", "sao", "tại", "vì", "và", "với", "của",
    "từ", "đến", "hay", "hoặc", "được", "có", "đã", "các",
    "những", "trong", "về", "cho",
}

def _tokenize_vi(text: str) -> str:
    """Segment Vietnamese text into compound words (e.g. 'khởi_nghĩa')."""
    try:
        from underthesea import word_tokenize
        return word_tokenize(text, format="text")
    except Exception:
        return text


def extract_entity(query: str) -> str:
    query = query.lower().strip()
    query = re.sub(r"[?.!,;:]+$", "", query).strip()

    # Pass 1: explicit definition-question suffixes
    patterns = [
        " là ai",
        " là gì",
        " là người nào",
        " khi nào",
        " ở đâu",
    ]
    for p in patterns:
        if query.endswith(p):
            return query[:-len(p)].strip()

    # Pass 2: bare noun phrase — short query with no question/function vocabulary
    # Handles "Hùng Vương", "Ngô Quyền", "Hai Bà Trưng", etc.
    words = query.split()
    if 1 <= len(words) <= 5 and not any(w in _BARE_ENTITY_EXCLUDES for w in words):
        return query

    return ""

# ─── BM25 Index ───────────────────────────────────────────────────────────────

class BM25Index:
    """In-memory BM25Okapi index over Vietnamese-tokenised chunk text."""

    def __init__(self, chunks: list[dict]):
        from rank_bm25 import BM25Okapi
        print("📑 Building BM25 index...")
        self.chunks = chunks
        corpus = [
            _tokenize_vi(c.get("text", "").lower()).split()
            for c in chunks
        ]
        self.index = BM25Okapi(corpus)
        print(f"   BM25 index built over {len(corpus)} chunks\n")

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        tokens = _tokenize_vi(query.lower()).split()
        scores = self.index.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


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
            self.bm25_index = BM25Index(self.chunks)
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
        with open(chunk_path, encoding="utf-8") as f:
            self.chunks = json.load(f)

        print(f"   {len(self.chunks)} chunks loaded\n")

        # DEBUG
        print("\n===== HUNG VUONG CHECK =====")

        for chunk in self.chunks:
            text = chunk.get("text", "").lower()

            if "hùng vương" in text:
                print(chunk["chunk_id"])
                print(chunk["title"])
                print(chunk["text"][:1000])
                print()

        print("===========================\n")

        self.bm25_index = BM25Index(self.chunks)

    def search(
        self,
        query: str,
        top_k: int = TOP_K,
        dynasty_context: Optional[str] = None,
    ) -> list[dict]:
        """
        Hybrid BM25 + Vector search fused via Reciprocal Rank Fusion,
        then boosted by dynasty context / entity phrase / keyword signals.
        """

        candidate_k = top_k * 2

        # --------------------------------------------------
        # Step 1: Vector search (segmented query)
        # --------------------------------------------------

        segmented_query = _tokenize_vi(query)

        q_vec = self.model.encode(
            [segmented_query],
            normalize_embeddings=True,
        )[0]

        vec_scores = self.vectors @ q_vec
        vec_ranked = sorted(
            enumerate(vec_scores), key=lambda x: x[1], reverse=True
        )[:candidate_k]

        # --------------------------------------------------
        # Step 2: BM25 search
        # --------------------------------------------------

        bm25_ranked = self.bm25_index.search(query, top_k=candidate_k)

        # --------------------------------------------------
        # Step 3: Reciprocal Rank Fusion  (K = 60)
        # --------------------------------------------------

        K = 60
        rrf_scores: dict[int, float] = {}

        for rank, (chunk_idx, _) in enumerate(vec_ranked):
            rrf_scores[chunk_idx] = rrf_scores.get(chunk_idx, 0.0) + 1 / (K + rank + 1)

        for rank, (chunk_idx, _) in enumerate(bm25_ranked):
            rrf_scores[chunk_idx] = rrf_scores.get(chunk_idx, 0.0) + 1 / (K + rank + 1)

        # --------------------------------------------------
        # Query preprocessing for boost passes
        # --------------------------------------------------

        entity = extract_entity(query)

        stopwords = {
            'là', 'ai', 'gì', 'như_thế_nào', 'tại_sao', 'và', 'của', 'có', 'được',
            'đã', 'các', 'những', 'trong', 'về', 'cho', 'với', 'tại', 'ở', 'lại',
            'xuất_hiện', 'hiện_nay', 'như_vậy', 'vì_sao', 'bởi_vì',
        }

        query_clean = re.sub(r"[^\w\s]", "", segmented_query.lower())
        query_words = set(query_clean.split())
        keywords = {w for w in query_words - stopwords if '_' in w or len(w) > 4}

        segmented_dynasty = _tokenize_vi(dynasty_context).lower() if dynasty_context else None
        dynasty_lower     = dynasty_context.lower()              if dynasty_context else None

        print("\n" + "=" * 60)
        print("QUERY:", query)
        print("SEGMENTED:", segmented_query)
        print("ENTITY:", entity)
        print("KEYWORDS:", keywords)

        vec_top3 = [
            f"[{self.chunks[idx].get('chunk_id')}, {s:.3f}]"
            for idx, s in vec_ranked[:3]
        ]
        bm25_top3 = [
            f"[{self.chunks[idx].get('chunk_id')}, {s:.3f}]"
            for idx, s in bm25_ranked[:3]
        ]
        print("VECTOR TOP 3:", ", ".join(vec_top3))
        print("BM25 TOP 3:  ", ", ".join(bm25_top3))
        print("=" * 60)

        # --------------------------------------------------
        # Step 4: Apply boosts on RRF scores
        # --------------------------------------------------

        for chunk_idx, base in list(rrf_scores.items()):

            chunk      = self.chunks[chunk_idx]
            text_lower  = chunk.get("text", "").lower()
            title_lower = chunk.get("title", "").lower()

            # dynasty context boost — highest priority
            if dynasty_lower:
                if (
                    dynasty_lower in text_lower
                    or dynasty_lower in title_lower
                    or (segmented_dynasty and (
                        segmented_dynasty in text_lower
                        or segmented_dynasty in title_lower
                    ))
                ):
                    rrf_scores[chunk_idx] = base + 8.0

            if entity and len(entity.split()) >= 2:
                # entity phrase boost — precise match only
                if entity in title_lower:
                    rrf_scores[chunk_idx] = rrf_scores[chunk_idx] + 3.0
                    print(
                        f"ENTITY TITLE HIT -> "
                        f"{chunk.get('chunk_id')} | "
                        f"{chunk.get('title')}"
                    )
                elif entity in text_lower:
                    rrf_scores[chunk_idx] = rrf_scores[chunk_idx] + 5.0
                    print(f"ENTITY TEXT HIT -> {chunk.get('chunk_id')}")
            else:
                # keyword boost — compound words matched in space form
                hits = sum(
                    1
                    for kw in keywords
                    if kw.replace('_', ' ') in text_lower
                    or kw.replace('_', ' ') in title_lower
                )
                if hits:
                    rrf_scores[chunk_idx] = rrf_scores[chunk_idx] + hits * 1.0

        # --------------------------------------------------
        # Step 5: Return top_k by final score
        # --------------------------------------------------

        ranked_final = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        print("\n========== RETRIEVAL DEBUG ==========")
        print("RRF FINAL:")

        for rank, (chunk_idx, score) in enumerate(ranked_final, start=1):
            chunk = self.chunks[chunk_idx]
            print(
                f"[{rank}] "
                f"score={score:.4f} | "
                f"id={chunk.get('chunk_id')} | "
                f"title={chunk.get('title')}"
            )

        print("====================================\n")

        results = []
        for chunk_idx, score in ranked_final:
            chunk = self.chunks[chunk_idx].copy()
            chunk["score"] = score
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
            LIMIT 10
        """, entities=entities, chunk_ids=chunk_ids)

        return {
            "entities":        entities,
            "relations":       relations,
            "neighbor_chunks": neighbor_chunks,
        }

    def lookup_entity(self, entity_name: str) -> Optional[dict]:
        """
        Lookup an entity node by name for definition queries ("là ai / là gì").
        Falls back to fetching title-matched chunks as surrogate description
        when the node has no description field.
        """
        rows = self._run("""
            MATCH (n)
            WHERE toLower(coalesce(n.name, n.text)) = toLower($name)
              AND (n:Person OR n:Dynasty OR n:Place OR n:Event)
            RETURN labels(n)[0]              AS type,
                   coalesce(n.name, n.text)  AS name,
                   n.description             AS description,
                   n.aliases                 AS aliases,
                   n.mentions                AS mentions
            LIMIT 1
        """, name=entity_name)

        if not rows:
            return None

        info = dict(rows[0])

        # Fetch chunks whose title contains the entity name as surrogate context
        chunks = self._run("""
            MATCH (n)-[:MENTIONED_IN]->(c:Chunk)
            WHERE toLower(coalesce(n.name, n.text)) = toLower($name)
              AND toLower(c.title) CONTAINS toLower($name)
            RETURN c.chunk_id AS chunk_id, c.title AS title, c.text AS text
            ORDER BY c.chunk_id
            LIMIT 3
        """, name=entity_name)

        if chunks:
            info["context_chunks"] = chunks

        # For Person nodes without a description, look for Dynasty nodes that list
        # this person in their key_figures — gives curated dynasty-level context.
        if not info.get("description"):
            dynasty_rows = self._run("""
                MATCH (d:Dynasty)
                WHERE any(fig IN d.key_figures
                          WHERE toLower(fig) CONTAINS toLower($name))
                RETURN d.name             AS dynasty_name,
                       d.description      AS dynasty_description,
                       d.period           AS period,
                       d.key_events       AS key_events
                LIMIT 2
            """, name=entity_name)
            if dynasty_rows:
                info["related_dynasties"] = dynasty_rows

        return info


# ─── Step 3: Context Builder ──────────────────────────────────────────────────

def build_context(
    query: str,
    vector_chunks: list[dict],
    graph_data: dict,
    entity_info: Optional[dict] = None,
) -> str:
    """
    Gom tất cả context thành 1 string để đưa vào LLM.
    Format rõ ràng để Claude dễ tham chiếu.
    """
    parts = []

    # A. Entity knowledge – injected first so LLM sees the definition before chunks
    if entity_info:
        parts.append("## Thông tin tra cứu nhân vật / địa danh\n")
        ename = entity_info.get("name", "")
        parts.append(f"**{ename}**")
        aliases = entity_info.get("aliases") or []
        if aliases:
            parts.append(f"Tên khác: {', '.join(aliases)}")
        if entity_info.get("description"):
            parts.append(entity_info["description"])

        # Dynasty-level context when the Person node has no own description
        for d in (entity_info.get("related_dynasties") or []):
            dname = d.get("dynasty_name", "")
            period = d.get("period", "")
            desc = d.get("dynasty_description", "")
            events = d.get("key_events") or []
            parts.append(
                f"\nTriều đại liên quan: {dname} ({period})"
                + (f"\n{desc}" if desc else "")
                + (f"\nSự kiện chính: {'; '.join(events[:3])}" if events else "")
            )

        ctx_chunks = entity_info.get("context_chunks") or []
        if ctx_chunks:
            parts.append("\nĐoạn văn trong sử liệu:")
            for ch in ctx_chunks:
                parts.append(f"[~] {ch['title']}")
                parts.append(ch["text"][:600])
                parts.append("")
        parts.append("")

    # B. Chunks từ vector search
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
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Thiếu OPENAI_API_KEY trong .env")
        self.client = OpenAI(api_key=api_key)

    def generate(self, query: str, context: str) -> str:
        prompt = f"""Bạn là chuyên gia lịch sử Việt Nam. Chỉ dùng thông tin từ context sau để trả lời.
QUAN TRỌNG: Chỉ trả lời dựa trên thông tin có trong context. Nếu context không đề cập, hãy nói "Không có thông tin trong tài liệu."

Context:
{context}

Câu hỏi: {query}

Trả lời bằng tiếng Việt, súc tích và chính xác:"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
        )
        return response.choices[0].message.content


# ─── Main GraphRAG Pipeline ───────────────────────────────────────────────────

class GraphRAG:
    def __init__(self):
        self.embed_store = EmbeddingStore()
        self.embed_store.build()
        for chunk in self.embed_store.chunks:
            if chunk["title"] == "Hùng Vương.":
                print(chunk["chunk_id"])
        self.expander    = GraphExpander()
        self.generator   = ClaudeGenerator()
        print("✅ GraphRAG ready\n")

    def query(self, question: str, verbose: bool = True) -> str:
        if verbose:
            print(f"❓ Query: {question}\n")

        # Step 1: Detect entity from query intent ("là ai" / "là gì")
        entity = extract_entity(question)

        # Step 2: Entity knowledge lookup in Neo4j
        entity_info = None
        if entity:
            try:
                entity_info = self.expander.lookup_entity(entity)
                if entity_info:
                    ctx_count = len(entity_info.get("context_chunks") or [])
                    print(
                        f"🔎 Entity node found: {entity_info.get('name')} "
                        f"[{entity_info.get('type')}] — {ctx_count} title-matched chunk(s)"
                    )
                else:
                    print(f"⚠️  No entity node found for: '{entity}'")
            except Exception as exc:
                print(f"⚠️  Entity lookup failed: {exc}")

        # Step 3: Vector search
        vector_chunks = self.embed_store.search(question, top_k=TOP_K)
        chunk_ids = [c["chunk_id"] for c in vector_chunks]

        print("\n========= TOP RETRIEVED CHUNKS =========")
        for chunk in vector_chunks[:5]:
            print("\n====================")
            print("TITLE:", chunk["title"])
            print("SCORE:", chunk["score"])
            print(chunk["text"][:1000])
        print("\n========================================")

        if verbose:
            print(f"🔍 Vector search → {len(vector_chunks)} chunks:")
            for c in vector_chunks:
                print(f"   [{c['score']:.3f}] {c['title']}")

        # Step 4: Graph expansion
        graph_data = self.expander.expand(chunk_ids)
        if verbose:
            print(f"\n🕸️  Graph expansion:")
            print(f"   Entities    : {len(graph_data['entities'])}")
            print(f"   Relations   : {len(graph_data['relations'])}")
            print(f"   Extra chunks: {len(graph_data['neighbor_chunks'])}")

        # Step 5: Build context — entity info injected first when available
        context = build_context(question, vector_chunks, graph_data, entity_info=entity_info)

        # Step 6: Generate
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