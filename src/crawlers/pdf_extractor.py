"""
PDF Extractor: Đại Việt Sử Ký Toàn Thư
Bản dịch Viện KHXH Việt Nam (1993) — text-based PDF, tiếng Việt hiện đại.

Usage:
    python src/crawlers/pdf_extractor.py --pdf data/raw/dvsktt.pdf

Output:
    data/raw/dvsktt_raw.json  (merge với data cũ hoặc thay thế)
"""

import re
import os
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import Optional

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw")

# ─── Dynasty period mapping (bản dịch hiện đại 1993) ─────────────────────────

SECTION_TO_DYNASTY = {
    # Ngoại Kỷ
    "Kỷ Hồng Bàng":          "nhà Hồng Bàng",
    "Kinh Dương Vương":       "nhà Hồng Bàng",
    "Lạc Long Quân":          "nhà Hồng Bàng",
    "Hùng Vương":             "nhà Hồng Bàng",
    "Kỷ họ Thục":             "nhà Thục",
    "An Dương Vương":         "nhà Thục",
    "Kỷ họ Triệu":            "nhà Triệu",
    "Triệu Vũ Đế":            "nhà Triệu",
    "Triệu Văn Vương":        "nhà Triệu",
    "Triệu Minh Vương":       "nhà Triệu",
    "Triệu Ai Vương":         "nhà Triệu",
    "Triệu Vệ Dương Vương":   "nhà Triệu",
    "thuộc Tây Hán":          "nhà Hán",
    "Trưng Nữ Vương":         "Khởi nghĩa Hai Bà Trưng",
    "thuộc Đông Hán":         "nhà Hán",
    "Sĩ Vương":               "nhà Hán",
    "thuộc Ngô":              "Bắc thuộc",
    "tiền Lý":                "nhà Tiền Lý",
    "Lý Nam Đế":              "nhà Tiền Lý",
    "Triệu Việt Vương":       "nhà Tiền Lý",
    "Hậu Lý":                 "nhà Tiền Lý",
    "thuộc Tùy":              "nhà Đường",
    "thuộc Đường":            "nhà Đường",
    "họ Ngô":                 "nhà Ngô",
    "Ngô Vương":              "nhà Ngô",
    "Nam Bắc phân tranh":     "nhà Ngô",
    "Ngô sứ quân":            "nhà Ngô",
    # Bản Kỷ
    "nhà Đinh":               "nhà Đinh",
    "Đinh Tiên Hoàng":        "nhà Đinh",
    "nhà Lê":                 "nhà Tiền Lê",
    "Lê Đại Hành":            "nhà Tiền Lê",
    "nhà Lý":                 "nhà Lý",
    "Lý Thái Tổ":             "nhà Lý",
    "Lý Thái Tông":           "nhà Lý",
    "Lý Thánh Tông":          "nhà Lý",
    "Lý Nhân Tông":           "nhà Lý",
    "Lý Anh Tông":            "nhà Lý",
    "Lý Cao Tông":            "nhà Lý",
    "nhà Trần":               "nhà Trần",
    "Trần Thái Tông":         "nhà Trần",
    "Trần Thánh Tông":        "nhà Trần",
    "Trần Nhân Tông":         "nhà Trần",
    "Trần Anh Tông":          "nhà Trần",
    "Trần Minh Tông":         "nhà Trần",
    "nhà Hồ":                 "nhà Hồ",
    "Hồ Quý Ly":              "nhà Hồ",
    "Hậu Trần":               "nhà Hồ",
    "thuộc Minh":             "Bắc thuộc Minh",
    "Lê Hoàng Triều":         "nhà Hậu Lê",
    "Lê Thái Tổ":             "nhà Hậu Lê",
    "Lê Thái Tông":           "nhà Hậu Lê",
    "Lê Thánh Tông":          "nhà Hậu Lê",
}

# Markers nhận biết section mới trong PDF
SECTION_MARKERS = [
    r"^Kỷ\s+.+",
    r"^[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ][a-zàáảãạăắằẳẵặâấầẩẫậđêếềểễệôốồổỗộơớờởỡợưứừửữự]+\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ][a-zàáảãạăắằẳẵặâấầẩẫậđêếềểễệôốồổỗộơớờởỡợưứừửữự]+.*Vương$",
    r"^(Lý|Trần|Lê|Đinh|Ngô|Hồ)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰ].+",
]


@dataclass
class RawPage:
    source:        str = "dvsktt_pdf"
    tap:           str = ""
    cuon:          str = ""
    title:         str = ""
    url:           str = ""
    raw_text:      str = ""
    paragraphs:    list = field(default_factory=list)
    year_mentions: list = field(default_factory=list)
    dynasty_period:str = "unknown"


def infer_dynasty(title: str) -> str:
    for key, dynasty in SECTION_TO_DYNASTY.items():
        if key.lower() in title.lower():
            return dynasty
    return "unknown"


def extract_years(text: str) -> list:
    patterns = [
        r"\d{1,4}\s*(?:TCN|SCN|trước Công nguyên|sau Công nguyên)",
        r"năm\s+\d{3,4}",
        r"thế\s+kỷ\s+(?:I{1,3}|IV|V{1,3}|IX|X{1,3}|XI{1,2}|XIV|XV)",
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text, re.IGNORECASE))
    return list(set(found))


def clean_text(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFC", text)
    # Xóa số trang dạng [1a], [2b]...
    text = re.sub(r"\[\d+[ab]?\]", "", text)
    # Xóa footnote numbers
    text = re.sub(r"\d{1,3}$", "", text, flags=re.MULTILINE)
    # Chuẩn hóa khoảng trắng
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_by_sections(full_text: str) -> list[tuple[str, str]]:
    """
    Tách text thành các section theo title.
    Trả về list of (title, content).
    """
    # Tìm các dòng là title của section
    lines = full_text.split("\n")
    sections = []
    current_title = "Mở đầu"
    current_lines = []

    # Các pattern nhận biết title
    title_patterns = [
        r"^Kỷ\s+\S",
        r"^(Kinh Dương|Lạc Long|Hùng Vương|An Dương|Triệu Vũ|Triệu Văn|Trưng|Sĩ Vương)",
        r"^(Lý|Trần|Lê|Đinh|Ngô|Hồ)\s+(Thái|Thánh|Nhân|Anh|Cao|Minh|Tiên|Đại|Quý)",
        r"^(Đinh Tiên Hoàng|Lê Đại Hành|Ngô Quyền|Hậu Ngô Vương)",
    ]

    for line in lines:
        line = line.strip()
        if not line:
            current_lines.append("")
            continue

        is_title = any(re.match(p, line) for p in title_patterns)

        if is_title and len(current_lines) > 5:
            content = "\n".join(current_lines).strip()
            if len(content) > 100:
                sections.append((current_title, content))
            current_title = line
            current_lines = []
        else:
            current_lines.append(line)

    # Flush cuối
    if current_lines:
        content = "\n".join(current_lines).strip()
        if len(content) > 100:
            sections.append((current_title, content))

    return sections


def extract_pdf(pdf_path: str, start_page: int = 20, max_pages: int = None) -> list[RawPage]:
    """
    Extract text từ PDF và chia thành các section theo triều đại.
    start_page: bỏ qua phần mục lục đầu sách
    """
    try:
        import pdfplumber
    except ImportError:
        print("Cài pdfplumber: pip install pdfplumber")
        return []

    print(f"📖 Đọc PDF: {pdf_path}")
    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        end = min(total, start_page + max_pages) if max_pages else total
        print(f"   Tổng trang: {total} | Xử lý: {start_page} → {end}")

        full_text = ""
        for i, page in enumerate(pdf.pages[start_page:end], start=start_page):
            text = page.extract_text()
            if text:
                full_text += text + "\n"

            if (i - start_page) % 100 == 0:
                print(f"   Trang {i}/{end}...")

    print(f"   Extracted {len(full_text):,} chars")

    # Clean
    full_text = clean_text(full_text)

    # Split thành sections
    sections = split_by_sections(full_text)
    print(f"   Tìm thấy {len(sections)} sections")

    # Tạo RawPage objects
    raw_pages = []
    for title, content in sections:
        dynasty = infer_dynasty(title)
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 40]

        page = RawPage(
            source        = "dvsktt_pdf",
            title         = title,
            raw_text      = content,
            paragraphs    = paragraphs,
            year_mentions = extract_years(content),
            dynasty_period= dynasty,
        )
        raw_pages.append(page)

    return raw_pages


def save(pages: list[RawPage], output_dir: str = OUTPUT_DIR, merge: bool = True):
    """
    Lưu output. Nếu merge=True, gộp với dvsktt_raw.json cũ.
    """
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "dvsktt_raw.json")

    new_data = [asdict(p) for p in pages]

    if merge and os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            old_data = json.load(f)
        # Bỏ các trang cũ từ dvsktt_pdf để tránh duplicate
        old_data = [d for d in old_data if d.get("source") != "dvsktt_pdf"]
        combined = old_data + new_data
        print(f"💾 Merge: {len(old_data)} cũ + {len(new_data)} mới = {len(combined)} trang")
    else:
        combined = new_data
        print(f"💾 Save: {len(combined)} trang")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"   → {out_path}")

    # Stats
    total_words = sum(len(p.raw_text.split()) for p in pages)
    from collections import Counter
    dynasty_dist = Counter(p.dynasty_period for p in pages)
    print(f"\n📊 Stats:")
    print(f"   Pages         : {len(pages)}")
    print(f"   Total words   : {total_words:,}")
    print(f"\n   Dynasty distribution:")
    for dynasty, count in dynasty_dist.most_common():
        print(f"   {dynasty:30s}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf",        default="data/raw/dvsktt.pdf")
    parser.add_argument("--start-page", type=int, default=20,
                        help="Bỏ qua N trang đầu (mục lục, lời tựa)")
    parser.add_argument("--max-pages",  type=int, default=None,
                        help="Số trang tối đa cần xử lý (None = tất cả)")
    parser.add_argument("--no-merge",   action="store_true",
                        help="Thay thế dvsktt_raw.json thay vì merge")
    args = parser.parse_args()

    pages = extract_pdf(
        pdf_path   = args.pdf,
        start_page = args.start_page,
        max_pages  = args.max_pages,
    )

    if pages:
        save(pages, merge=not args.no_merge)
        print(f"\n✅ Done! Chạy tiếp:")
        print(f"   python src/parsers/text_cleaner.py")
        print(f"   python src/parsers/ner_extractor.py")
        print(f"   python src/graph/graph_builder.py")
    else:
        print("❌ Không extract được gì.")