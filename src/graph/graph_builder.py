"""
Phase 3 — Graph Builder
Import entities + relations từ NER output vào Neo4j AuraDB.

Schema:
  Nodes : Person, Dynasty, Place, Event, Time, Chunk
  Edges : CON_CUA, SINH_RA, KET_HON, CAI_TRI, DONG_DO_TAI,
          LAP_NUOC, DANH, TRUYEN_NGOI,
          MENTIONED_IN (entity → chunk),
          BELONGS_TO   (chunk → source)
"""

import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

ENTITIES_DIR = os.path.join(os.path.dirname(__file__), "../../data/entities")
NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# ─── Neo4j driver wrapper ─────────────────────────────────────────────────────

class GraphDB:
    def __init__(self):
        if not NEO4J_URI or not NEO4J_PASSWORD:
            raise ValueError("Thiếu NEO4J_URI hoặc NEO4J_PASSWORD trong .env")
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print(f"✅ Kết nối Neo4j: {NEO4J_URI}")

    def close(self):
        self.driver.close()

    def run(self, query: str, **params):
        with self.driver.session() as session:
            return session.run(query, **params).data()

    def run_batch(self, query: str, batch: list[dict]):
        with self.driver.session() as session:
            session.run(query, batch=batch)


# ─── Schema setup ─────────────────────────────────────────────────────────────

CONSTRAINTS = [
    "CREATE CONSTRAINT person_name  IF NOT EXISTS FOR (n:Person)  REQUIRE n.name  IS UNIQUE",
    "CREATE CONSTRAINT dynasty_name IF NOT EXISTS FOR (n:Dynasty) REQUIRE n.name  IS UNIQUE",
    "CREATE CONSTRAINT place_name   IF NOT EXISTS FOR (n:Place)   REQUIRE n.name  IS UNIQUE",
    "CREATE CONSTRAINT event_name   IF NOT EXISTS FOR (n:Event)   REQUIRE n.name  IS UNIQUE",
    "CREATE CONSTRAINT time_text    IF NOT EXISTS FOR (n:Time)    REQUIRE n.text  IS UNIQUE",
    "CREATE CONSTRAINT chunk_id     IF NOT EXISTS FOR (n:Chunk)   REQUIRE n.chunk_id IS UNIQUE",
]

def setup_schema(db: GraphDB):
    print("📐 Tạo constraints...")
    for c in CONSTRAINTS:
        try:
            db.run(c)
        except Exception as e:
            print(f"  [WARN] {e}")
    print("   Done\n")


# ─── Import nodes ─────────────────────────────────────────────────────────────

def import_chunks(db: GraphDB, records: list[dict]):
    batch = [{
        "chunk_id":      r["chunk_id"],
        "source":        r["source"],
        "title":         r["title"],
        "text":          r["text"][:500],
        "dynasty_period": r.get("dynasty_period", "unknown"),  
    } for r in records]

    db.run_batch("""
        UNWIND $batch AS row
        MERGE (c:Chunk {chunk_id: row.chunk_id})
        SET c.source         = row.source,
            c.title          = row.title,
            c.text           = row.text,
            c.dynasty_period = row.dynasty_period
    """, batch)
    print(f"   Chunks : {len(batch)}")


def import_entities(db: GraphDB, records: list[dict]):
    """Import tất cả entity nodes theo type."""
    counts = {t: 0 for t in ["PERSON","DYNASTY","PLACE","EVENT","TIME"]}

    # Gom tất cả entities unique
    entity_map: dict[str, dict] = {}
    for r in records:
        for e in r["entities"]:
            key = f"{e['type']}:{e['text']}"
            if key not in entity_map:
                entity_map[key] = e
            else:
                entity_map[key]["mentions"] = \
                    entity_map[key].get("mentions", 1) + e.get("mentions", 1)

    # Import theo từng type
    for etype, label, id_field in [
        ("PERSON",  "Person",  "name"),
        ("DYNASTY", "Dynasty", "name"),
        ("PLACE",   "Place",   "name"),
        ("EVENT",   "Event",   "name"),
        ("TIME",    "Time",    "text"),
    ]:
        batch = [
            {
                "name":     e["text"],
                "aliases":  e.get("aliases", []),
                "mentions": e.get("mentions", 1),
            }
            for e in entity_map.values() if e["type"] == etype
        ]
        if not batch:
            continue

        db.run_batch(f"""
            UNWIND $batch AS row
            MERGE (n:{label} {{{id_field}: row.name}})
            SET n.aliases  = row.aliases,
                n.mentions = row.mentions,
                n.source   = 'dvsktt'
        """, batch)
        counts[etype] = len(batch)

    for t, c in counts.items():
        print(f"   {t:8s}: {c} nodes")


# ─── Import edges ──────────────────────────────────────────────────────────────

def import_mentioned_in(db: GraphDB, records: list[dict]):
    """Entity → Chunk: MENTIONED_IN"""
    batch = []
    for r in records:
        for e in r["entities"]:
            batch.append({
                "entity_text": e["text"],
                "entity_type": e["type"],
                "chunk_id":    r["chunk_id"],
                "title":       r["title"],
            })

    # Xử lý từng type riêng vì label động
    for etype, label, id_field in [
        ("PERSON",  "Person",  "name"),
        ("DYNASTY", "Dynasty", "name"),
        ("PLACE",   "Place",   "name"),
        ("EVENT",   "Event",   "name"),
        ("TIME",    "Time",    "text"),
    ]:
        type_batch = [b for b in batch if b["entity_type"] == etype]
        if not type_batch:
            continue
        db.run_batch(f"""
            UNWIND $batch AS row
            MATCH (e:{label} {{{id_field}: row.entity_text}})
            MATCH (c:Chunk {{chunk_id: row.chunk_id}})
            MERGE (e)-[:MENTIONED_IN {{title: row.title}}]->(c)
        """, type_batch)

    print(f"   MENTIONED_IN: {len(batch)} edges")


def import_relations(db: GraphDB, records: list[dict]):
    """Import semantic relations từ RelationExtractor."""
    batch = []
    for r in records:
        for rel in r["relations"]:
            batch.append({
                "subject":   rel["subject"],
                "predicate": rel["predicate"],
                "object":    rel["object"],
                "evidence":  rel["evidence"][:200],
                "chunk_id":  r["chunk_id"],
            })

    if not batch:
        print("   Relations: 0 (chưa có — sẽ bổ sung sau)")
        return

    # Tạo relation giữa bất kỳ node nào có tên khớp
    db.run_batch("""
        UNWIND $batch AS row
        MATCH (a) WHERE (a.name = row.subject OR a.text = row.subject)
        MATCH (b) WHERE (b.name = row.object  OR b.text = row.object)
        CALL apoc.create.relationship(a, row.predicate, {
            evidence: row.evidence,
            chunk_id: row.chunk_id
        }, b) YIELD rel
        RETURN count(rel)
    """, batch)
    print(f"   Relations : {len(batch)} edges")


def import_relations_simple(db: GraphDB, records: list[dict]):
    """
    Fallback nếu APOC không có — dùng predicate cố định.
    Chỉ import các relation type đã biết.
    """
    predicates = {
        "CON_CUA":     "CON_CUA",
        "SINH_RA":     "SINH_RA",
        "KET_HON":     "KET_HON",
        "CAI_TRI":     "CAI_TRI",
        "DONG_DO_TAI": "DONG_DO_TAI",
        "LAP_NUOC":    "LAP_NUOC",
        "DANH":        "DANH",
        "TRUYEN_NGOI": "TRUYEN_NGOI",
    }

    total = 0
    for pred_key, pred_label in predicates.items():
        batch = [
            {
                "subject":  r["subject"],
                "object":   r["object"],
                "evidence": r["evidence"][:200],
                "chunk_id": rec["chunk_id"],
            }
            for rec in records
            for r in rec["relations"]
            if r["predicate"] == pred_key
        ]
        if not batch:
            continue

        db.run_batch(f"""
            UNWIND $batch AS row
            MATCH (a) WHERE a.name = row.subject OR a.text = row.subject
            MATCH (b) WHERE b.name = row.object  OR b.text = row.object
            MERGE (a)-[r:{pred_label}]->(b)
            SET r.evidence = row.evidence,
                r.chunk_id = row.chunk_id
        """, batch)
        total += len(batch)

    print(f"   Relations : {total} edges")


# ─── Co-occurrence edges ───────────────────────────────────────────────────────

def import_cooccurrence(db: GraphDB, records: list[dict]):
    """
    Tạo edge CO_OCCURS_WITH giữa các entity xuất hiện cùng chunk.
    Đây là nguồn relation quan trọng cho GraphRAG khi semantic relation ít.
    """
    batch = []
    for r in records:
        entities = [e for e in r["entities"] if e["type"] in ("PERSON","DYNASTY","PLACE","EVENT")]
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                a, b = entities[i], entities[j]
                if a["text"] != b["text"]:
                    batch.append({
                        "name_a":    a["text"],
                        "type_a":    a["type"],
                        "name_b":    b["text"],
                        "type_b":    b["type"],
                        "chunk_id":  r["chunk_id"],
                        "title":     r["title"],
                    })

    if not batch:
        print("   CO_OCCURS : 0")
        return

    db.run_batch("""
        UNWIND $batch AS row
        MATCH (a) WHERE (a.name = row.name_a OR a.text = row.name_a)
        MATCH (b) WHERE (b.name = row.name_b OR b.text = row.name_b)
        WITH a, b, row WHERE a <> b
        MERGE (a)-[r:CO_OCCURS_WITH]-(b)
        ON CREATE SET r.count = 1, r.chunks = [row.chunk_id]
        ON MATCH  SET r.count = r.count + 1,
                      r.chunks = CASE WHEN row.chunk_id IN r.chunks
                                      THEN r.chunks
                                      ELSE r.chunks + row.chunk_id END
    """, batch)
    print(f"   CO_OCCURS : {len(batch)} pairs")


# ─── Verify ───────────────────────────────────────────────────────────────────

def verify(db: GraphDB):
    print("\n📊 Thống kê graph:")
    for label in ["Chunk", "Person", "Dynasty", "Place", "Event", "Time"]:
        count = db.run(f"MATCH (n:{label}) RETURN count(n) AS c")[0]["c"]
        print(f"   {label:10s}: {count:>4} nodes")

    for rel in ["MENTIONED_IN", "CO_OCCURS_WITH", "CON_CUA", "SINH_RA", "LAP_NUOC"]:
        count = db.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c")[0]["c"]
        if count > 0:
            print(f"   {rel:20s}: {count:>4} edges")

    print("\n🔍 Sample query — Ai được nhắc đến nhiều nhất?")
    rows = db.run("""
        MATCH (p:Person)-[r:MENTIONED_IN]->()
        RETURN p.name AS name, count(r) AS mentions
        ORDER BY mentions DESC LIMIT 5
    """)
    for row in rows:
        print(f"   {row['name']} ({row['mentions']} lần)")


# ─── Main pipeline ─────────────────────────────────────────────────────────────

def build_graph():
    # Load data
    entities_path = os.path.join(ENTITIES_DIR, "dvsktt_entities.json")
    print(f"📂 Đọc: {entities_path}")
    with open(entities_path, encoding="utf-8") as f:
        records = json.load(f)
    print(f"   {len(records)} chunks\n")

    db = GraphDB()
    try:
        # 1. Schema
        setup_schema(db)

        # 2. Nodes
        print("📥 Import nodes...")
        import_chunks(db, records)
        import_entities(db, records)

        # 3. Edges
        print("\n🔗 Import edges...")
        import_mentioned_in(db, records)
        import_relations_simple(db, records)
        import_cooccurrence(db, records)

        # 4. Verify
        verify(db)

    finally:
        db.close()
        print("\n✅ Done!")


if __name__ == "__main__":
    build_graph()