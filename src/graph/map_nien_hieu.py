"""
Map remaining unknown chunks using niên hiệu (reign title) matching.
Run AFTER map_chunks_to_dynasties.py

Usage:
    python src/graph/map_nien_hieu.py
"""

import os
import re
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# ─── Niên hiệu → Dynasty mapping ─────────────────────────────────────────────
# Each entry: (niên hiệu list, dynasty name)

NIEN_HIEU_MAP = [
    # ── nhà Lý ────────────────────────────────────────────────────────────────
    (["Thuận Thiên", "Gia Khánh", "Thiên Thành", "Thông Thụy", "Càn Phù Hữu Đạo",
      "Thiên Cảm Thánh Vũ", "Sùng Hưng Đại Bảo", "Long Thụy Thái Bình",
      "Chương Thánh Gia Khánh", "Long Chương Thiên Tự", "Thiên Huống Bảo Tượng",
      "Thần Vũ", "Anh Vũ Chiêu Thắng", "Quảng Hựu", "Hội Phong", "Long Phù",
      "Hội Tường Đại Khánh", "Thiên Phù Duệ Vũ", "Thiên Phù Khánh Thọ",
      "Thiên Thuận", "Thiên Chương Bảo Tự", "Đại Định", "Chính Long Bảo Ứng",
      "Thiên Cảm Chí Bảo", "Trinh Phù", "Thiên Tư Gia Thụy", "Thiên Gia Bảo Hựu",
      "Trị Bình Long Ứng", "Kiến Gia"], "nhà Lý"),

    # ── nhà Trần ──────────────────────────────────────────────────────────────
    (["Kiến Trung", "Thiên Ứng Chính Bình", "Nguyên Phong", "Thiệu Long",
      "Bảo Phù", "Thiệu Bảo", "Trùng Hưng", "Hưng Long", "Anh Tông",
      "Đại Khánh", "Khai Thái", "Thiệu Phong", "Đại Trị", "Xương Phù",
      "Quang Thái", "Kiến Tân", "Thiệu Khánh", "Long Khánh",
      "Đại Định Trần", "Trùng Quang"], "nhà Trần"),

    # ── nhà Hồ ────────────────────────────────────────────────────────────────
    (["Thánh Nguyên", "Khai Đại"], "nhà Hồ"),

    # ── Bắc thuộc Minh ────────────────────────────────────────────────────────
    (["Vĩnh Lạc", "Hồng Hy", "Tuyên Đức", "thuộc Minh", "Trương Phụ",
      "Hậu Trần", "Trùng Quang"], "Bắc thuộc Minh"),

    # ── nhà Hậu Lê ────────────────────────────────────────────────────────────
    (["Thuận Thiên Lê", "Thiệu Bình", "Đại Bảo", "Thái Hòa", "Diên Ninh",
      "Thiên Hưng", "Quang Thuận", "Hồng Đức", "Cảnh Thống", "Đoan Khánh",
      "Hồng Thuận", "Quang Thiệu", "Đại Chính", "Nguyên Hòa", "Vĩnh Định",
      "Thuần Phúc", "Chính Trị", "Hồng Phúc", "Gia Thái", "Quang Hưng",
      "Hoằng Định", "Đức Long", "Dương Hòa", "Phúc Thái", "Khánh Đức",
      "Thịnh Đức", "Vĩnh Thọ", "Vạn Khánh", "Cảnh Trị", "Dương Đức",
      "Đức Nguyên", "Vĩnh Trị", "Chính Hòa", "Bảo Thái", "Vĩnh Khánh",
      "Long Đức", "Vĩnh Hựu", "Cảnh Hưng", "Lam Sơn"], "nhà Hậu Lê"),

    # ── nhà Đinh ──────────────────────────────────────────────────────────────
    (["Thái Bình Đinh"], "nhà Đinh"),

    # ── nhà Tiền Lê ───────────────────────────────────────────────────────────
    (["Thiên Phúc", "Hưng Thống", "Ứng Thiên", "Cảnh Thụy"], "nhà Tiền Lê"),

    # ── nhà Ngô ───────────────────────────────────────────────────────────────
    (["Hậu Ngô", "Ngô Xương Ngập", "Ngô Xương Văn", "Nam Tấn Vương",
      "Thiên Sách"], "nhà Ngô"),

    # ── Bắc thuộc Tùy Đường ───────────────────────────────────────────────────
    (["Đường Nguyên Hòa", "Đường Trường Khánh", "Nguyên Hòa Đường",
      "Hội Xương", "Đại Trung", "Hàm Thông", "Càn Phù Đường", "Quang Khải",
      "Kiến Ninh", "Tường Phù Đường", "Vũ Đức", "Trinh Quán", "Vĩnh Huy",
      "Thần Long", "Khai Nguyên", "Thiên Bảo Đường",
      "Khúc Thừa Dụ", "Khúc Hạo", "Khúc Thừa Mỹ"], "Bắc thuộc Tùy Đường"),

    # ── Bắc thuộc lần 2 ───────────────────────────────────────────────────────
    (["Kiến Hành Ngô", "Tống Nguyên Gia", "Tề", "Lương Đại Đồng",
      "Đại Bảo Lương", "Thái Thanh"], "Bắc thuộc lần 2"),

    # ── nhà Tiền Lý ───────────────────────────────────────────────────────────
    (["Thiên Đức Lý", "Đại Đức Lý", "Tiền Lý"], "nhà Tiền Lý"),
]


def match_nien_hieu(text: str) -> str | None:
    """Match text against niên hiệu patterns."""
    text_lower = text.lower()
    for keywords, dynasty in NIEN_HIEU_MAP:
        for kw in keywords:
            if kw.lower() in text_lower:
                return dynasty
    return None


def extract_reign_year(title: str) -> str | None:
    """
    Extract dynasty from title pattern like:
    'Kỷ Giáp Tý, [Thuận Thiên] năm thứ 10'
    """
    # Match [niên hiệu] pattern
    match = re.search(r'\[([^\]]+)\]', title)
    if match:
        nien_hieu = match.group(1)
        return match_nien_hieu(nien_hieu)
    return None


def map_nien_hieu():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        # Load only unknown chunks
        print("📂 Loading unknown chunks...")
        chunks = session.run("""
            MATCH (c:Chunk)
            WHERE c.dynasty_period = 'unknown' OR c.dynasty_period IS NULL
            RETURN c.chunk_id AS chunk_id, c.title AS title, c.text AS text
        """).data()
        print(f"   {len(chunks)} unknown chunks\n")

        updates = []
        stats = {"title": 0, "text": 0, "still_unknown": 0}

        for chunk in chunks:
            title = chunk["title"] or ""
            text  = chunk["text"]  or ""

            # 1. Try niên hiệu in title first (most reliable)
            dynasty = extract_reign_year(title)
            if dynasty:
                stats["title"] += 1
            else:
                # 2. Try keyword match in full text
                dynasty = match_nien_hieu(title + " " + text[:300])
                if dynasty:
                    stats["text"] += 1
                else:
                    stats["still_unknown"] += 1

            if dynasty:
                updates.append({
                    "chunk_id": chunk["chunk_id"],
                    "dynasty":  dynasty,
                })

        print(f"📊 Niên hiệu mapping results:")
        print(f"   From title   : {stats['title']}")
        print(f"   From text    : {stats['text']}")
        print(f"   Still unknown: {stats['still_unknown']}")
        print(f"   Total mapped : {len(updates)}\n")

        # Update Neo4j
        if updates:
            print("💾 Updating dynasty_period in Neo4j...")
            session.run("""
                UNWIND $updates AS row
                MATCH (c:Chunk {chunk_id: row.chunk_id})
                SET c.dynasty_period = row.dynasty
            """, updates=updates)
            print(f"   Updated {len(updates)} chunks")

        # Update BELONGS_TO_DYNASTY edges
        print("\n🔗 Updating BELONGS_TO_DYNASTY edges...")
        result = session.run("""
            MATCH (c:Chunk), (d:Dynasty)
            WHERE c.dynasty_period = d.name
              AND NOT (c)-[:BELONGS_TO_DYNASTY]->(d)
            MERGE (c)-[:BELONGS_TO_DYNASTY]->(d)
            RETURN count(*) AS created
        """).data()
        print(f"   Created {result[0]['created']} new edges")

        # Final distribution
        print("\n📋 Final dynasty distribution:")
        rows = session.run("""
            MATCH (c:Chunk)
            RETURN c.dynasty_period AS dynasty, count(*) AS count
            ORDER BY count DESC
        """).data()

        total = sum(r["count"] for r in rows)
        for r in rows:
            pct = r["count"] / total * 100
            bar = "█" * min(int(r["count"] / 30), 30)
            print(f"   {r['dynasty']:35s}: {r['count']:4d} ({pct:4.1f}%) {bar}")

    driver.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    map_nien_hieu()