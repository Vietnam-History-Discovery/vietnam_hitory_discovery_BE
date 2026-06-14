"""
Parser & Cleaner: xử lý text thô từ DVSKTT và Wikipedia
Bước này chuẩn bị data sạch cho NER và Graph building (Phase 2-3)
"""

import json
import re
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

RAW_DIR    = os.path.join(os.path.dirname(__file__), "../../data/raw")
PARSED_DIR = os.path.join(os.path.dirname(__file__), "../../data/parsed")


# ─── Dynasty period mapping ───────────────────────────────────────────────────

TITLE_TO_DYNASTY = {
    # Hồng Bàng
    "Kinh dương Vương":     "nhà Hồng Bàng",
    "Lạc long Quân":        "nhà Hồng Bàng",
    "Hùng Vương":           "nhà Hồng Bàng",
    "Cuốn thứ nhất":        "nhà Hồng Bàng",
    # Thục
    "An dương Vương":       "nhà Thục",
    # Triệu
    "Vũ đế":                "nhà Triệu",
    "Văn Vương":            "nhà Triệu",
    "Minh Vương":           "nhà Triệu",
    "Ai Vương":             "nhà Triệu",
    "Vệ dương Vương":       "nhà Triệu",
    # Hán (Bắc thuộc)
    "Đời thuộc về Tây Hán": "nhà Hán",
    "Đời thuộc về Đông Hán":"nhà Hán",
    "Đời thuộc Đông Hán":   "nhà Hán",
    "Đời thuộc Tây Hán":    "nhà Hán",
    # Trưng Vương
    "Triều Trưng Nữ Vương": "Khởi nghĩa Hai Bà Trưng",
    # Sĩ Vương
    "Triều Sĩ Vương":       "nhà Hán",
    # Ngô Tấn Tống...
    "Đời thuộc về Ngô, Tấn, Tống, Tề, Lương": "Bắc thuộc",
    # Tiền Lý
    "Đời Tiền Lý":          "nhà Tiền Lý",
    "Đời Triệu Việt Vương": "nhà Tiền Lý",
    "Đời hậu Lý":           "nhà Tiền Lý",
    # Đường
    "Đời thuộc Tùy và Đường": "nhà Đường",
    # Nam Bắc phân tranh
    "Đời Nam Bắc phân tranh": "nhà Ngô",
    # Ngô
    "Đời Ngô":              "nhà Ngô",
    "Hậu Ngô Vương":        "nhà Ngô",
    "Ngô sứ quân":          "nhà Ngô",
}

def infer_dynasty(title: str) -> str:
    """Xác định triều đại từ title của trang."""
    # Exact match trước
    if title in TITLE_TO_DYNASTY:
        return TITLE_TO_DYNASTY[title]
    # Partial match
    for key, dynasty in TITLE_TO_DYNASTY.items():
        if key.lower() in title.lower() or title.lower() in key.lower():
            return dynasty
    return "unknown"


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    chunk_id:       str
    source:         str
    tap:            str
    cuon:           str
    title:          str
    url:            str
    text:           str
    char_count:     int
    word_count:     int
    dynasty_period: str = "unknown"          # ← MỚI
    year_mentions:  list = field(default_factory=list)


# ─── Cleaner ─────────────────────────────────────────────────────────────────

class VietnameseTextCleaner:
    OCR_NOISE = [
        (r"[—–]+", "—"),
        (r"\.{3,}", "…"),
        (r"\s*\n\s*\n\s*", "\n\n"),
        (r" {2,}", " "),
        (r"\[(\d+)\]", ""),
        (r"↑", ""),
        (r"Lấy từ \"https?://[^\"]+\"", ""),
    ]

    def clean(self, text: str) -> str:
        import unicodedata
        text = unicodedata.normalize("NFC", text)
        text = "".join(c for c in text if c.isprintable() or c in "\n\t")
        for pattern, replacement in self.OCR_NOISE:
            text = re.sub(pattern, replacement, text)
        return text.strip()


# ─── Chunker ─────────────────────────────────────────────────────────────────

class TextChunker:
    def __init__(self, max_words=200, min_words=30, overlap_words=30):
        self.max_words     = max_words
        self.min_words     = min_words
        self.overlap_words = overlap_words

    def chunk_paragraphs(self, paragraphs: list) -> list:
        chunks = []
        buffer = ""
        for para in paragraphs:
            words = para.split()
            if not words:
                continue
            if len(words) < self.min_words:
                buffer = (buffer + " " + para).strip()
                continue
            if buffer:
                if len(buffer.split()) >= self.min_words:
                    chunks.append(buffer)
                buffer = ""
            if len(words) <= self.max_words:
                chunks.append(para)
            else:
                chunks.extend(self._sliding_window(words))
        if buffer and len(buffer.split()) >= self.min_words:
            chunks.append(buffer)
        return chunks

    def _sliding_window(self, words: list) -> list:
        result = []
        step = self.max_words - self.overlap_words
        i = 0
        while i < len(words):
            chunk_words = words[i: i + self.max_words]
            result.append(" ".join(chunk_words))
            if i + self.max_words >= len(words):
                break
            i += step
        return result


# ─── Main pipeline ───────────────────────────────────────────────────────────

class ParsePipeline:
    def __init__(self):
        self.cleaner = VietnameseTextCleaner()
        self.chunker = TextChunker()
        os.makedirs(PARSED_DIR, exist_ok=True)

    def process_dvsktt(self, raw_path: Optional[str] = None) -> list:
        if raw_path is None:
            raw_path = os.path.join(RAW_DIR, "dvsktt_raw.json")

        print(f"📂 Đọc raw data: {raw_path}")
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_pages = json.load(f)

        all_chunks = []
        chunk_counter = 0

        for page in raw_pages:
            title          = page.get("title", "")
            dynasty_period = infer_dynasty(title)

            cleaned_paras = []
            for para in page["paragraphs"]:
                cleaned = self.cleaner.clean(para)
                if cleaned:
                    cleaned_paras.append(cleaned)

            chunks_text = self.chunker.chunk_paragraphs(cleaned_paras)

            for chunk_text in chunks_text:
                chunk_counter += 1
                words = chunk_text.split()
                chunk = Chunk(
                    chunk_id      = f"dvsktt_{chunk_counter:04d}",
                    source        = "dvsktt",
                    tap           = page.get("tap", ""),
                    cuon          = page.get("cuon", ""),
                    title         = title,
                    url           = page.get("url", ""),
                    text          = chunk_text,
                    char_count    = len(chunk_text),
                    word_count    = len(words),
                    dynasty_period= dynasty_period,
                    year_mentions = page.get("year_mentions", []),
                )
                all_chunks.append(chunk)

        self._save(all_chunks, "dvsktt_chunks.json")
        self._print_stats(all_chunks)
        return all_chunks

    def process_wiki(self, raw_path: Optional[str] = None) -> list:
        if raw_path is None:
            raw_path = os.path.join(RAW_DIR, "wiki_raw.json")
        if not os.path.exists(raw_path):
            print("⚠️  Chưa có wiki_raw.json — chạy wiki_crawler.py trước")
            return []

        with open(raw_path, "r", encoding="utf-8") as f:
            raw_pages = json.load(f)

        all_chunks = []
        chunk_counter = 0

        for page in raw_pages:
            title          = page.get("title", "")
            dynasty_period = infer_dynasty(title)

            cleaned_paras = []
            for para in page.get("paragraphs", []):
                cleaned = self.cleaner.clean(para)
                if cleaned:
                    cleaned_paras.append(cleaned)

            chunks_text = self.chunker.chunk_paragraphs(cleaned_paras)

            for chunk_text in chunks_text:
                chunk_counter += 1
                words = chunk_text.split()
                chunk = Chunk(
                    chunk_id      = f"wiki_{chunk_counter:04d}",
                    source        = "wiki",
                    tap           = page.get("category", ""),
                    cuon          = "",
                    title         = title,
                    url           = page.get("url", ""),
                    text          = chunk_text,
                    char_count    = len(chunk_text),
                    word_count    = len(words),
                    dynasty_period= dynasty_period,
                )
                all_chunks.append(chunk)

        self._save(all_chunks, "wiki_chunks.json")
        self._print_stats(all_chunks, source="wiki")
        return all_chunks

    def _save(self, chunks: list, filename: str):
        out_path = os.path.join(PARSED_DIR, filename)
        data = [asdict(c) for c in chunks]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu {len(chunks)} chunks → {out_path}")

    def _print_stats(self, chunks: list, source: str = "dvsktt"):
        avg_words = sum(c.word_count for c in chunks) / max(len(chunks), 1)
        print(f"\n📊 Thống kê chunks [{source}]:")
        print(f"   Tổng chunks    : {len(chunks)}")
        print(f"   Avg words/chunk: {avg_words:.1f}")

        # In phân bố dynasty
        from collections import Counter
        dynasty_counts = Counter(c.dynasty_period for c in chunks)
        print(f"\n   Dynasty distribution:")
        for dynasty, count in dynasty_counts.most_common():
            print(f"   {dynasty:35s}: {count}")


if __name__ == "__main__":
    pipeline = ParsePipeline()
    dvsktt_chunks = pipeline.process_dvsktt()
    wiki_chunks   = pipeline.process_wiki()
    print(f"\n✅ Tổng cộng: {len(dvsktt_chunks) + len(wiki_chunks)} chunks")