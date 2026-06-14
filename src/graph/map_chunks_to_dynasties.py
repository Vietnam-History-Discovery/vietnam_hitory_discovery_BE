"""
Map Chunks to Dynasties based on year extraction from text.
Reads year from chunk text → finds matching dynasty by year range → updates dynasty_period.

Usage:
    python src/graph/map_chunks_to_dynasties.py
"""

import os
import re
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# ─── Dynasty year ranges ──────────────────────────────────────────────────────
# (start_year, end_year, dynasty_name)
# TCN = negative, SCN = positive

DYNASTY_RANGES = [
    (-2879, -258,  "nhà Hồng Bàng"),
    (-257,  -208,  "nhà Thục"),
    (-207,  -111,  "nhà Triệu"),
    (-111,   40,   "Bắc thuộc Hán"),
    (40,     43,   "Khởi nghĩa Hai Bà Trưng"),
    (43,    544,   "Bắc thuộc lần 2"),
    (544,   602,   "nhà Tiền Lý"),
    (602,   938,   "Bắc thuộc Tùy Đường"),
    (938,   967,   "nhà Ngô"),
    (968,   980,   "nhà Đinh"),
    (980,   1009,  "nhà Tiền Lê"),
    (1009,  1225,  "nhà Lý"),
    (1226,  1400,  "nhà Trần"),
    (1400,  1407,  "nhà Hồ"),
    (1407,  1427,  "Bắc thuộc Minh"),
    (1428,  1788,  "nhà Hậu Lê"),
]

# ─── Keyword fallback mapping ─────────────────────────────────────────────────
# Used when no year found in chunk

KEYWORD_MAP = [
    (["Hùng Vương", "Văn Lang", "Kinh Dương Vương", "Lạc Long Quân", "Xích Quỷ"],  "nhà Hồng Bàng"),
    (["An Dương Vương", "Âu Lạc", "Cổ Loa", "nỏ thần", "Mị Châu", "Trọng Thủy"],  "nhà Thục"),
    (["Triệu Đà", "Nam Việt", "Triệu Vũ Đế", "Phiên Ngung"],                        "nhà Triệu"),
    (["Trưng Trắc", "Trưng Nhị", "Hai Bà Trưng", "Tô Định"],                        "Khởi nghĩa Hai Bà Trưng"),
    (["Sĩ Nhiếp", "Sĩ Vương"],                                                       "Bắc thuộc lần 2"),
    (["Lý Bí", "Lý Nam Đế", "Vạn Xuân", "Triệu Quang Phục", "Triệu Việt Vương"],   "nhà Tiền Lý"),
    (["Phùng Hưng", "Khúc Thừa Dụ", "Khúc Hạo", "Dương Đình Nghệ"],               "Bắc thuộc Tùy Đường"),
    (["Ngô Quyền", "Bạch Đằng", "sứ quân", "Dương Tam Kha"],                        "nhà Ngô"),
    (["Đinh Tiên Hoàng", "Đinh Bộ Lĩnh", "Hoa Lư", "Đại Cồ Việt"],                "nhà Đinh"),
    (["Lê Hoàn", "Lê Đại Hành", "Lê Long Đĩnh"],                                   "nhà Tiền Lê"),
    (["Lý Thái Tổ", "Lý Thái Tông", "Lý Thánh Tông", "Lý Nhân Tông",
      "Lý Anh Tông", "Lý Cao Tông", "Lý Huệ Tông", "Thăng Long", "Lý Thường Kiệt"], "nhà Lý"),
    (["Trần Thái Tông", "Trần Thánh Tông", "Trần Nhân Tông", "Trần Anh Tông",
      "Trần Hưng Đạo", "quân Nguyên", "Nguyên Mông", "Trần Minh Tông"],             "nhà Trần"),
    (["Hồ Quý Ly", "Hồ Hán Thương", "Đại Ngu", "Tây Đô"],                          "nhà Hồ"),
    (["Hậu Trần", "thuộc Minh", "Trương Phụ"],                                      "Bắc thuộc Minh"),
    (["Lê Thái Tổ", "Lê Lợi", "Lam Sơn", "Bình Ngô", "Lê Thánh Tông",
      "Lê Thái Tông", "Nguyễn Trãi"],                                                "nhà Hậu Lê"),
]


# ─── Year extraction ──────────────────────────────────────────────────────────

def extract_year(text: str) -> int | None:
    """
    Extract the most prominent year from chunk text.
    Handles formats:
      - [1044] → 1044 SCN
      - (111 TCN) → -111
      - năm 938 → 938
      - 207 trước Công nguyên → -207
    """
    # Format [YYYY] — most common in DVSKTT biên niên sử
    bracket = re.findall(r'\[(\d{3,4})\]', text)
    if bracket:
        # Take first bracketed year that looks like a real year (not a footnote)
        for y in bracket:
            year = int(y)
            if 100 <= year <= 1900:
                return year

    # Format (YYYY TCN) or YYYY TCN
    tcn = re.findall(r'(\d{1,4})\s*(?:TCN|trước Công nguyên|trước Tây lịch)', text)
    if tcn:
        return -int(tcn[0])

    # Format YYYY SCN or năm YYYY
    scn = re.findall(r'năm\s+(\d{3,4})', text)
    if scn:
        year = int(scn[0])
        if 40 <= year <= 1900:
            return year

    # Bare 4-digit year in parentheses like (938)
    paren = re.findall(r'\((\d{3,4})\)', text)
    if paren:
        for y in paren:
            year = int(y)
            if 200 <= year <= 1900:
                return year

    return None


def year_to_dynasty(year: int) -> str | None:
    """Map a year to dynasty name using year ranges."""
    for start, end, name in DYNASTY_RANGES:
        if start <= year <= end:
            return name
    return None


def keyword_to_dynasty(text: str) -> str | None:
    """Fallback: match dynasty using keyword search."""
    text_lower = text.lower()
    for keywords, dynasty in KEYWORD_MAP:
        for kw in keywords:
            if kw.lower() in text_lower:
                return dynasty
    return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def map_chunks_to_dynasties():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        # Load all chunks
        print("📂 Loading chunks from Neo4j...")
        chunks = session.run("""
            MATCH (c:Chunk)
            RETURN c.chunk_id AS chunk_id, c.title AS title,
                   c.text AS text, c.dynasty_period AS dynasty_period
        """).data()
        print(f"   {len(chunks)} chunks loaded\n")

        # Map each chunk
        updates = []
        stats = {"year": 0, "keyword": 0, "unknown": 0}

        for chunk in chunks:
            text = (chunk["title"] or "") + " " + (chunk["text"] or "")

            # Try year-based first
            year = extract_year(text)
            dynasty = year_to_dynasty(year) if year else None
            method = "year"

            # Fallback to keyword
            if not dynasty:
                dynasty = keyword_to_dynasty(text)
                method = "keyword"

            if dynasty:
                updates.append({
                    "chunk_id": chunk["chunk_id"],
                    "dynasty":  dynasty,
                })
                stats[method] += 1
            else:
                stats["unknown"] += 1

        print(f"📊 Mapping results:")
        print(f"   Year-based   : {stats['year']}")
        print(f"   Keyword-based: {stats['keyword']}")
        print(f"   Unknown      : {stats['unknown']}")
        print(f"   Total mapped : {stats['year'] + stats['keyword']}/{len(chunks)}\n")

        # Batch update in Neo4j
        print("💾 Updating dynasty_period in Neo4j...")
        session.run("""
            UNWIND $updates AS row
            MATCH (c:Chunk {chunk_id: row.chunk_id})
            SET c.dynasty_period = row.dynasty
        """, updates=updates)
        print(f"   Updated {len(updates)} chunks")

        # Create BELONGS_TO_DYNASTY edges
        print("\n🔗 Creating BELONGS_TO_DYNASTY edges...")
        result = session.run("""
            MATCH (c:Chunk), (d:Dynasty)
            WHERE c.dynasty_period = d.name
            MERGE (c)-[:BELONGS_TO_DYNASTY]->(d)
            RETURN count(*) AS created
        """).data()
        print(f"   Created {result[0]['created']} edges")

        # Final stats
        print("\n📋 Dynasty distribution:")
        rows = session.run("""
            MATCH (c:Chunk)
            RETURN c.dynasty_period AS dynasty, count(*) AS count
            ORDER BY count DESC
        """).data()
        for r in rows:
            bar = "█" * min(int(r["count"] / 20), 30)
            print(f"   {r['dynasty']:35s}: {r['count']:4d} {bar}")

    driver.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    map_chunks_to_dynasties()