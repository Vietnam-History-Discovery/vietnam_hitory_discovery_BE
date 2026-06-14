"""
Seed Dynasty nodes in Neo4j with proper historical metadata.
Run this AFTER graph_builder.py

Usage:
    python src/graph/seed_dynasties.py
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# ─── Dynasty definitions ──────────────────────────────────────────────────────

DYNASTIES = [
    # ── Huyền sử ──────────────────────────────────────────────────────────────
    {
        "name":        "nhà Hồng Bàng",
        "period":      "2879 TCN – 258 TCN",
        "start_year":  -2879,
        "end_year":    -258,
        "era":         "Huyền sử",
        "capital":     "Phong Châu",
        "description": "Triều đại huyền sử đầu tiên của người Việt, từ Kinh Dương Vương đến 18 đời Hùng Vương. Lập nước Văn Lang.",
        "key_figures": ["Kinh Dương Vương", "Lạc Long Quân", "Âu Cơ", "Hùng Vương"],
        "key_events":  ["Lập nước Văn Lang", "Huyền thoại con Rồng cháu Tiên"],
    },
    {
        "name":        "nhà Thục",
        "period":      "257 TCN – 208 TCN",
        "start_year":  -257,
        "end_year":    -208,
        "era":         "Huyền sử",
        "capital":     "Cổ Loa",
        "description": "An Dương Vương Thục Phán diệt Văn Lang, lập nước Âu Lạc, xây thành Cổ Loa và chế nỏ thần.",
        "key_figures": ["An Dương Vương", "Mị Châu", "Trọng Thủy", "Thần Kim Quy"],
        "key_events":  ["Lập nước Âu Lạc", "Xây thành Cổ Loa", "Nỏ thần"],
    },
    {
        "name":        "nhà Triệu",
        "period":      "207 TCN – 111 TCN",
        "start_year":  -207,
        "end_year":    -111,
        "era":         "Bắc thuộc",
        "capital":     "Phiên Ngung",
        "description": "Triệu Đà lập nước Nam Việt, thôn tính Âu Lạc. Tranh chấp với nhà Hán cho đến khi bị diệt năm 111 TCN.",
        "key_figures": ["Triệu Đà", "Triệu Văn Vương", "Triệu Minh Vương"],
        "key_events":  ["Lập nước Nam Việt", "Thôn tính Âu Lạc", "Nam Việt bị Hán diệt"],
    },

    # ── Bắc thuộc ─────────────────────────────────────────────────────────────
    {
        "name":        "Bắc thuộc Hán",
        "period":      "111 TCN – 40 SCN",
        "start_year":  -111,
        "end_year":    40,
        "era":         "Bắc thuộc",
        "capital":     "Luy Lâu",
        "description": "Giai đoạn đầu Bắc thuộc dưới sự cai trị của nhà Hán. Người Việt bị đồng hóa nhưng vẫn giữ bản sắc.",
        "key_figures": ["Sĩ Nhiếp", "Tô Định"],
        "key_events":  ["Nam Việt bị Hán diệt", "Giao Chỉ - Cửu Chân thành quận Hán"],
    },
    {
        "name":        "Khởi nghĩa Hai Bà Trưng",
        "period":      "40 SCN – 43 SCN",
        "start_year":  40,
        "end_year":    43,
        "era":         "Bắc thuộc",
        "capital":     "Mê Linh",
        "description": "Trưng Trắc và Trưng Nhị khởi nghĩa đánh đuổi Tô Định, giành độc lập ngắn ngủi trước khi bị Mã Viện đàn áp.",
        "key_figures": ["Trưng Trắc", "Trưng Nhị", "Tô Định", "Mã Viện", "Thi Sách"],
        "key_events":  ["Khởi nghĩa Hai Bà Trưng", "Đánh chiếm 65 thành", "Trưng Vương lên ngôi"],
    },
    {
        "name":        "Bắc thuộc lần 2",
        "period":      "43 SCN – 544 SCN",
        "start_year":  43,
        "end_year":    544,
        "era":         "Bắc thuộc",
        "capital":     "Luy Lâu",
        "description": "Giai đoạn Bắc thuộc dài nhất, dưới sự cai trị của Đông Hán, Ngô, Tấn, Tống, Tề, Lương. Nhiều cuộc khởi nghĩa nổ ra.",
        "key_figures": ["Sĩ Nhiếp", "Bà Triệu"],
        "key_events":  ["Khởi nghĩa Bà Triệu (248)", "Sĩ Nhiếp cai trị"],
    },

    # ── Độc lập ngắn ──────────────────────────────────────────────────────────
    {
        "name":        "nhà Tiền Lý",
        "period":      "544 SCN – 602 SCN",
        "start_year":  544,
        "end_year":    602,
        "era":         "Độc lập",
        "capital":     "Long Biên",
        "description": "Lý Bí khởi nghĩa đánh đuổi quân Lương, lập nước Vạn Xuân. Triệu Quang Phục (Triệu Việt Vương) tiếp tục kháng chiến.",
        "key_figures": ["Lý Bí", "Lý Nam Đế", "Triệu Quang Phục", "Triệu Việt Vương"],
        "key_events":  ["Khởi nghĩa Lý Bí", "Lập nước Vạn Xuân", "Triệu Việt Vương kháng Lương"],
    },
    {
        "name":        "Bắc thuộc Tùy Đường",
        "period":      "602 SCN – 938 SCN",
        "start_year":  602,
        "end_year":    938,
        "era":         "Bắc thuộc",
        "capital":     "Tống Bình",
        "description": "Bắc thuộc dưới nhà Tùy rồi nhà Đường. Phùng Hưng, Khúc Thừa Dụ dần giành quyền tự chủ.",
        "key_figures": ["Phùng Hưng", "Khúc Thừa Dụ", "Khúc Hạo", "Dương Đình Nghệ"],
        "key_events":  ["Phùng Hưng khởi nghĩa", "Khúc Thừa Dụ tự chủ (905)", "Dương Đình Nghệ"],
    },

    # ── Thời kỳ độc lập ───────────────────────────────────────────────────────
    {
        "name":        "nhà Ngô",
        "period":      "938 – 967",
        "start_year":  938,
        "end_year":    967,
        "era":         "Độc lập",
        "capital":     "Cổ Loa",
        "description": "Ngô Quyền đại phá quân Nam Hán trên sông Bạch Đằng (938), chấm dứt Bắc thuộc. Sau loạn 12 sứ quân.",
        "key_figures": ["Ngô Quyền", "Dương Tam Kha", "Ngô Xương Ngập"],
        "key_events":  ["Trận Bạch Đằng 938", "Ngô Quyền xưng vương", "Loạn 12 sứ quân"],
    },
    {
        "name":        "nhà Đinh",
        "period":      "968 – 980",
        "start_year":  968,
        "end_year":    980,
        "era":         "Độc lập",
        "capital":     "Hoa Lư",
        "description": "Đinh Bộ Lĩnh dẹp loạn 12 sứ quân, thống nhất đất nước, lập ra nước Đại Cồ Việt.",
        "key_figures": ["Đinh Tiên Hoàng", "Đinh Bộ Lĩnh", "Lê Hoàn"],
        "key_events":  ["Dẹp loạn 12 sứ quân", "Lập Đại Cồ Việt", "Đinh Tiên Hoàng bị ám sát"],
    },
    {
        "name":        "nhà Tiền Lê",
        "period":      "980 – 1009",
        "start_year":  980,
        "end_year":    1009,
        "era":         "Độc lập",
        "capital":     "Hoa Lư",
        "description": "Lê Hoàn (Lê Đại Hành) lên ngôi, đánh bại quân Tống và Chiêm Thành, bảo vệ độc lập.",
        "key_figures": ["Lê Hoàn", "Lê Đại Hành", "Lê Long Đĩnh"],
        "key_events":  ["Đánh bại quân Tống (981)", "Chinh phạt Chiêm Thành"],
    },
    {
        "name":        "nhà Lý",
        "period":      "1009 – 1225",
        "start_year":  1009,
        "end_year":    1225,
        "era":         "Độc lập",
        "capital":     "Thăng Long",
        "description": "Triều đại hưng thịnh nhất thời kỳ phong kiến Việt Nam. Dời đô về Thăng Long, phát triển văn hóa Phật giáo.",
        "key_figures": ["Lý Thái Tổ", "Lý Thái Tông", "Lý Thánh Tông", "Lý Nhân Tông", "Lý Thường Kiệt"],
        "key_events":  ["Dời đô về Thăng Long (1010)", "Đánh bại Tống (1077)", "Lập Văn Miếu"],
    },
    {
        "name":        "nhà Trần",
        "period":      "1226 – 1400",
        "start_year":  1226,
        "end_year":    1400,
        "era":         "Độc lập",
        "capital":     "Thăng Long",
        "description": "Ba lần đánh bại quân Nguyên Mông. Phát triển văn học chữ Nôm và Phật giáo Trúc Lâm.",
        "key_figures": ["Trần Thái Tông", "Trần Hưng Đạo", "Trần Nhân Tông", "Trần Quốc Tuấn"],
        "key_events":  ["3 lần kháng Nguyên (1258, 1285, 1288)", "Trận Bạch Đằng 1288", "Phật giáo Trúc Lâm"],
    },
    {
        "name":        "nhà Hồ",
        "period":      "1400 – 1407",
        "start_year":  1400,
        "end_year":    1407,
        "era":         "Độc lập",
        "capital":     "Tây Đô",
        "description": "Hồ Quý Ly cướp ngôi nhà Trần, đổi tên nước thành Đại Ngu. Thực hiện nhiều cải cách nhưng bị nhà Minh xâm lược.",
        "key_figures": ["Hồ Quý Ly", "Hồ Hán Thương"],
        "key_events":  ["Hồ Quý Ly lên ngôi", "Quân Minh xâm lược (1407)"],
    },
    {
        "name":        "Bắc thuộc Minh",
        "period":      "1407 – 1427",
        "start_year":  1407,
        "end_year":    1427,
        "era":         "Bắc thuộc",
        "capital":     "Đông Quan",
        "description": "20 năm đô hộ của nhà Minh. Lê Lợi khởi nghĩa Lam Sơn giành lại độc lập.",
        "key_figures": ["Lê Lợi", "Nguyễn Trãi"],
        "key_events":  ["Khởi nghĩa Lam Sơn (1418)", "Bình Ngô đại cáo"],
    },
    {
        "name":        "nhà Hậu Lê",
        "period":      "1428 – 1788",
        "start_year":  1428,
        "end_year":    1788,
        "era":         "Độc lập",
        "capital":     "Thăng Long",
        "description": "Triều đại tồn tại lâu nhất trong lịch sử Việt Nam. Lê Thánh Tông đưa đất nước đến đỉnh cao phát triển.",
        "key_figures": ["Lê Thái Tổ", "Lê Thánh Tông", "Nguyễn Trãi"],
        "key_events":  ["Lê Lợi lên ngôi (1428)", "Hồng Đức thịnh thế", "Trịnh Nguyễn phân tranh"],
    },
]


# ─── Seed script ──────────────────────────────────────────────────────────────

def seed_dynasties():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        # Clear old Dynasty nodes
        print("🗑️  Clearing old Dynasty nodes...")
        session.run("MATCH (d:Dynasty) DETACH DELETE d")

        # Create new Dynasty nodes
        print("🏛️  Creating Dynasty nodes...")
        for d in DYNASTIES:
            session.run("""
                MERGE (d:Dynasty {name: $name})
                SET d.period      = $period,
                    d.start_year  = $start_year,
                    d.end_year    = $end_year,
                    d.era         = $era,
                    d.capital     = $capital,
                    d.description = $description,
                    d.key_figures = $key_figures,
                    d.key_events  = $key_events,
                    d.source      = 'seed'
            """, **d)
            print(f"   ✓ {d['name']} ({d['period']})")

        # Verify
        count = session.run("MATCH (d:Dynasty) RETURN count(d) AS c").data()[0]["c"]
        print(f"\n✅ Created {count} Dynasty nodes")

        # Show all
        rows = session.run("""
            MATCH (d:Dynasty)
            RETURN d.name AS name, d.period AS period, d.era AS era
            ORDER BY d.start_year
        """).data()

        print("\n📋 All dynasties (chronological):")
        current_era = None
        for r in rows:
            if r["era"] != current_era:
                current_era = r["era"]
                print(f"\n  [{current_era}]")
            print(f"    {r['name']:30s} {r['period']}")

    driver.close()


if __name__ == "__main__":
    seed_dynasties()