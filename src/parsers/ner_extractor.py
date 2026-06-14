"""
Phase 2 — NER Extractor
Hỗ trợ cả 2 dạng viết:
  - Hiện đại: Văn Lang, Âu Lạc, Hùng Vương
  - Cổ (bản dịch 1945): Văn-Lang, Âu-Lạc, Hùng-vương
"""

import json, re, os
from dataclasses import dataclass, field, asdict
from typing import Optional

PARSED_DIR   = os.path.join(os.path.dirname(__file__), "../../data/parsed")
ENTITIES_DIR = os.path.join(os.path.dirname(__file__), "../../data/entities")


# ─── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Entity:
    text:     str
    type:     str
    aliases:  list[str] = field(default_factory=list)
    mentions: int = 1

@dataclass
class Relation:
    subject:   str
    predicate: str
    object:    str
    evidence:  str


# ─── Helper: normalize ────────────────────────────────────────────────────────

def norm(text: str) -> str:
    """Chuẩn hoá về dạng lowercase, bỏ dấu gạch ngang kiểu cổ."""
    return re.sub(r"-", " ", text).lower().strip()


# ─── Từ điển thực thể ─────────────────────────────────────────────────────────
# Mỗi entry: (tên chuẩn, [aliases bao gồm cả dạng cổ])

PERSON_DICT = [
    ("Kinh Dương Vương",  ["Lộc Tục", "Kinh-Dương-Vương", "Kinh-Dương-vương"]),
    ("Lạc Long Quân",     ["Sùng Lãm", "Lạc-Long-Quân", "Lạc-Long-quân"]),
    ("Âu Cơ",             ["Âu-Cơ"]),
    ("Hùng Vương",        ["Hùng-Vương", "Hùng-vương"]),
    ("An Dương Vương",    ["Thục Phán", "An-Dương-Vương", "An-Dương-vương", "An dương Vương"]),
    ("Mị Châu",           ["Mị-Châu"]),
    ("Trọng Thủy",        ["Trọng-Thủy"]),
    ("Triệu Đà",          ["Triệu-Đà", "Triệu Vũ Đế", "Triệu-Vũ-Đế"]),
    ("Trưng Trắc",        ["Trưng-Trắc", "Trưng Vương", "Trưng-Vương"]),
    ("Trưng Nhị",         ["Trưng-Nhị"]),
    ("Tô Định",           ["Tô-Định"]),
    ("Mã Viện",           ["Mã-Viện"]),
    ("Thi Sách",          ["Thi-Sách"]),
    ("Đế Minh",           ["Đế-Minh"]),
    ("Đế Nghi",           ["Đế-Nghi"]),
    ("Đế Lai",            ["Đế-Lai"]),
    ("Vụ Tiên",           ["Vụ-Tiên"]),
    ("Long Nữ",           ["Long-Nữ"]),
    ("Thần Kim Quy",      ["Thần-Kim-Quy", "Kim Quy", "Kim-Quy"]),
    ("Lý Bí",             ["Lý-Bí", "Lý Nam Đế", "Lý-Nam-Đế"]),
    ("Triệu Quang Phục",  ["Triệu-Quang-Phục", "Triệu Việt Vương", "Triệu-Việt-Vương"]),
    ("Phùng Hưng",        ["Phùng-Hưng"]),
    ("Ngô Quyền",         ["Ngô-Quyền"]),
    ("Đinh Bộ Lĩnh",      ["Đinh-Bộ-Lĩnh", "Đinh Tiên Hoàng", "Đinh-Tiên-Hoàng"]),
    ("Lê Hoàn",           ["Lê-Hoàn", "Lê Đại Hành", "Lê-Đại-Hành"]),
    ("Lý Thái Tổ",        ["Lý-Thái-Tổ", "Lý Công Uẩn", "Lý-Công-Uẩn"]),
    ("Trần Thái Tông",    ["Trần-Thái-Tông"]),
    ("Trần Hưng Đạo",     ["Trần-Hưng-Đạo", "Hưng Đạo Vương", "Hưng-Đạo-Vương"]),
    ("Hồ Quý Ly",         ["Hồ-Quý-Ly"]),
    ("Lê Lợi",            ["Lê-Lợi", "Lê Thái Tổ", "Lê-Thái-Tổ"]),
    ("Lê Thánh Tông",     ["Lê-Thánh-Tông"]),
    ("Sĩ Nhiếp",          ["Sĩ-Nhiếp", "Sĩ Vương", "Sĩ-Vương"]),
]

DYNASTY_DICT = [
    ("nhà Hồng Bàng",  ["Hồng-Bàng", "họ Hồng Bàng", "triều Hồng Bàng"]),
    ("nhà Thục",       ["Triệu Thục", "Triệu-Thục", "nhà Thục"]),
    ("nhà Triệu",      ["Triệu-Đà", "Nam Việt", "Nam-Việt"]),
    ("nhà Hán",        ["Tây Hán", "Tây-Hán", "Đông Hán", "Đông-Hán", "nhà Tây Hán", "nhà Đông Hán"]),
    ("nhà Đường",      ["nhà-Đường", "đời Đường", "đời-Đường"]),
    ("nhà Ngô",        ["triều Ngô", "Ngô Vương"]),
    ("nhà Đinh",       ["triều Đinh", "Đinh-triều"]),
    ("nhà Tiền Lê",    ["nhà Lê Hoàn", "triều Lê Hoàn"]),
    ("nhà Lý",         ["triều Lý", "nhà-Lý", "đời Lý"]),
    ("nhà Trần",       ["triều Trần", "nhà-Trần", "đời Trần"]),
    ("nhà Hồ",         ["triều Hồ", "nhà-Hồ"]),
    ("nhà Hậu Lê",     ["Hậu Lê", "nhà Lê", "triều Lê", "nhà-Lê"]),
    ("nhà Nguyễn",     ["triều Nguyễn"]),
]

PLACE_DICT = [
    ("Phong Châu",     ["Phong-Châu", "Phú Thọ"]),
    ("Mê Linh",        ["Mê-Linh"]),
    ("Cổ Loa",         ["Cổ-Loa", "thành Cổ Loa", "Loa-Thành"]),
    ("Phiên Ngung",    ["Phiên-Ngung", "Quảng Châu"]),
    ("Văn Lang",       ["Văn-Lang", "nước Văn Lang", "nước Văn-Lang"]),
    ("Âu Lạc",         ["Âu-Lạc", "nước Âu Lạc", "nước Âu-Lạc"]),
    ("Xích Quỷ",       ["Xích-Quỷ", "nước Xích Quỷ"]),
    ("Nam Việt",       ["Nam-Việt", "nước Nam Việt"]),
    ("Giao Chỉ",       ["Giao-Chỉ", "quận Giao Chỉ"]),
    ("Cửu Chân",       ["Cửu-Chân", "quận Cửu Chân"]),
    ("Động Đình",      ["Động-Đình", "Động Đình Quân"]),
    ("Ngũ Lĩnh",       ["Ngũ-Lĩnh", "núi Ngũ Lĩnh"]),
    ("sông Hát",       ["Hát-Giang", "sông Hát Giang", "Hát Giang"]),
    ("Châu Diên",      ["Châu-Diên"]),
    ("Thăng Long",     ["Thăng-Long", "Đại La"]),
    ("Hoa Lư",         ["Hoa-Lư"]),
    ("Luy Lâu",        ["Luy-Lâu"]),
    ("Phong Khê",      ["Phong-Khê"]),
]

EVENT_DICT = [
    ("Khởi nghĩa Hai Bà Trưng",   ["khởi nghĩa", "Trưng", "Tô Định", "nổi dậy"]),
    ("Trận Bạch Đằng",             ["Bạch Đằng", "Bạch-Đằng"]),
    ("Kháng chiến chống Nguyên",   ["quân Nguyên", "Nguyên-Mông", "kháng Nguyên"]),
    ("Nước Văn Lang thành lập",    ["Hùng Vương", "Văn-Lang", "đặt tên nước"]),
    ("Nước Âu Lạc thành lập",      ["Âu-Lạc", "An-Dương-Vương", "An Dương Vương", "gồm có nước Văn-Lang"]),
    ("Âu Lạc diệt vong",           ["Âu-Lạc", "Triệu Đà", "Triệu-Đà", "thua chạy"]),
    ("Nam Việt thành lập",         ["Triệu Đà", "Triệu-Đà", "Nam Việt", "Nam-Việt", "xưng vương"]),
    ("Khởi nghĩa Lý Bí",           ["Lý Bí", "Lý-Bí", "Lý Nam Đế", "khởi nghĩa"]),
]


# ─── Rule-based NER ───────────────────────────────────────────────────────────

class RuleBasedNER:
    def __init__(self):
        self._person_map  = self._build_map(PERSON_DICT)
        self._dynasty_map = self._build_map(DYNASTY_DICT)
        self._place_map   = self._build_map(PLACE_DICT)
        self._time_re     = [
            re.compile(p, re.IGNORECASE) for p in [
                r"\d{1,4}\s*(?:TCN|SCN|trước Tây.lịch|trước Công nguyên|sau Công nguyên)",
                r"năm\s+\d{3,4}",
                r"thế\s+kỷ\s+(?:I{1,3}|IV|V{1,3}|IX|X{1,3}|XI{1,2}|XIV|XV)",
            ]
        ]

    @staticmethod
    def _build_map(dict_list):
        m = {}
        for canonical, aliases in dict_list:
            m[norm(canonical)] = canonical
            for alias in aliases:
                m[norm(alias)] = canonical
        return m

    def extract(self, text: str) -> list[Entity]:
        entities: dict[str, Entity] = {}
        text_norm = norm(text)

        def add(canonical, etype, aliases=[]):
            key = f"{etype}:{canonical}"
            if key in entities:
                entities[key].mentions += 1
            else:
                entities[key] = Entity(text=canonical, type=etype, aliases=aliases)

        for name_norm, canonical in self._person_map.items():
            if name_norm in text_norm:
                aliases = next((a for c, a in PERSON_DICT if c == canonical), [])
                add(canonical, "PERSON", aliases)

        for name_norm, canonical in self._dynasty_map.items():
            if name_norm in text_norm:
                aliases = next((a for c, a in DYNASTY_DICT if c == canonical), [])
                add(canonical, "DYNASTY", aliases)

        for name_norm, canonical in self._place_map.items():
            if name_norm in text_norm:
                aliases = next((a for c, a in PLACE_DICT if c == canonical), [])
                add(canonical, "PLACE", aliases)

        for event_name, keywords in EVENT_DICT:
            hits = sum(1 for kw in keywords if norm(kw) in text_norm)
            if hits >= 2:
                add(event_name, "EVENT")

        for pattern in self._time_re:
            for match in pattern.finditer(text):
                add(match.group().strip(), "TIME")

        return list(entities.values())


# ─── Relation extractor ───────────────────────────────────────────────────────

class RelationExtractor:
    PATTERNS = [
        (r"([\w\s\-]+?)\s+là con của\s+([\w\s\-]+?)[\.,]",       "CON_CUA"),
        (r"([\w\s\-]+?)\s+sinh ra\s+([\w\s\-]+?)[\.,]",           "SINH_RA"),
        (r"([\w\s\-]+?)\s+lấy\s+(?:con gái\s+[\w\s\-]+?\s+là\s+)?([\w\s\-]+?)[\.,]", "KET_HON"),
        (r"([\w\s\-]+?)\s+(?:cai trị|trị vì)\s+([\w\s\-]+?)[\.,]","CAI_TRI"),
        (r"([\w\s\-]+?)\s+đóng đô (?:ở|tại)\s+([\w\s\-]+?)[\.,]","DONG_DO_TAI"),
        (r"([\w\s\-]+?)\s+lập\s+(?:ra\s+)?(?:nước\s+)?([\w\s\-]+?)[\.,]","LAP_NUOC"),
        (r"([\w\s\-]+?)\s+đánh\s+([\w\s\-]+?)[\.,]",              "DANH"),
        (r"([\w\s\-]+?)\s+truyền ngôi cho\s+([\w\s\-]+?)[\.,]",   "TRUYEN_NGOI"),
    ]

    def __init__(self):
        self._compiled = [(re.compile(p, re.IGNORECASE | re.UNICODE), pred) for p, pred in self.PATTERNS]
        self._known = {norm(c) for c, _ in PERSON_DICT + DYNASTY_DICT + PLACE_DICT}

    def extract(self, text: str, entities: list[Entity]) -> list[Relation]:
        entity_set = {norm(e.text) for e in entities}
        relations  = []
        for sent in re.split(r'(?<=[.!?])\s+', text):
            if len(sent) < 15:
                continue
            for pattern, predicate in self._compiled:
                for m in pattern.finditer(sent):
                    s = self._clean(m.group(1))
                    o = self._clean(m.group(2))
                    if (norm(s) in entity_set or norm(s) in self._known or
                        norm(o) in entity_set or norm(o) in self._known):
                        if s and o and s != o:
                            relations.append(Relation(s, predicate, o, sent[:120]))
        return relations

    @staticmethod
    def _clean(name: str) -> str:
        for prefix in ["vua ", "bà ", "ông ", "con ", "người "]:
            if name.lower().startswith(prefix):
                name = name[len(prefix):]
        return name.strip()


# ─── Pipeline ─────────────────────────────────────────────────────────────────

class NERPipeline:
    def __init__(self):
        self.ner     = RuleBasedNER()
        self.rel_ext = RelationExtractor()
        os.makedirs(ENTITIES_DIR, exist_ok=True)

    def process(self, chunks_path: Optional[str] = None) -> list[dict]:
        if chunks_path is None:
            chunks_path = os.path.join(PARSED_DIR, "dvsktt_chunks.json")

        print(f"📂 Đọc chunks: {chunks_path}")
        with open(chunks_path, encoding="utf-8") as f:
            chunks = json.load(f)

        results = []
        stats: dict[str, set] = {t: set() for t in ["PERSON","DYNASTY","PLACE","EVENT","TIME"]}

        for chunk in chunks:
            entities  = self.ner.extract(chunk["text"])
            relations = self.rel_ext.extract(chunk["text"], entities)
            for e in entities:
                stats.get(e.type, set()).add(e.text)
            results.append({
                "chunk_id":       chunk["chunk_id"],
                "source":         chunk["source"],
                "title":          chunk["title"],
                "text":           chunk["text"],
                "dynasty_period": chunk.get("dynasty_period", "unknown"),  
                "entities":       [asdict(e) for e in entities],
                "relations":      [asdict(r) for r in relations],
            })

        # Save
        out = os.path.join(ENTITIES_DIR, "dvsktt_entities.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved → {out}")

        idx_out = os.path.join(ENTITIES_DIR, "entity_index.json")
        with open(idx_out, "w", encoding="utf-8") as f:
            json.dump({k: sorted(v) for k, v in stats.items()}, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved index → {idx_out}")

        # Stats
        print(f"\n📊 Kết quả NER:")
        print(f"   Chunks      : {len(results)}")
        print(f"   Entities    : {sum(len(r['entities']) for r in results)}")
        print(f"   Relations   : {sum(len(r['relations']) for r in results)}")
        print(f"\n   Unique entities:")
        for t, names in stats.items():
            sample = ', '.join(sorted(names)[:5])
            print(f"   {t:8s} ({len(names):2d}): {sample}")
        return results


if __name__ == "__main__":
    pipeline = NERPipeline()
    results  = pipeline.process()

    print("\n─── Sample chunk ───")
    r = results[0]
    print(f"Text: {r['text'][:150]}...")
    print(f"\nEntities:")
    for e in r["entities"]:
        print(f"  [{e['type']:8s}] {e['text']}")
    print(f"\nRelations:")
    for rel in r["relations"]:
        print(f"  {rel['subject']} --[{rel['predicate']}]--> {rel['object']}")
