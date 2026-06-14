"""
Crawler: Đại Việt Sử Ký Toàn Thư
Dùng auto-discovery: đọc trang mục lục → tìm tất cả link con → crawl từng trang.
Không hardcode URL → không bao giờ bị 404 do đoán sai.
"""

import requests, time, json, re, os
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from typing import Optional
from tqdm import tqdm
from urllib.parse import urljoin, urlparse

BASE_URL   = "https://vi.wikisource.org"
ROOT_PATH  = "/wiki/%C4%90%E1%BA%A1i_Vi%E1%BB%87t_s%E1%BB%AD_k%C3%BD_to%C3%A0n_th%C6%B0"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw")
HEADERS    = {
    "User-Agent": "VietnamHistoryRAG/1.0 (academic research)",
    "Accept-Language": "vi,en;q=0.9",
}

# Prefix URL của bộ sách — chỉ lấy link nằm trong bộ này
BOOK_PREFIX = "%C4%90%E1%BA%A1i_Vi%E1%BB%87t_s%E1%BB%AD_k%C3%BD_to%C3%A0n_th%C6%B0"

# Trang chỉ là mục lục, không có nội dung thật — bỏ qua
SKIP_TITLES = {
    "Đại Việt sử ký toàn thư",
    "Đại Việt sử ký toàn thư/Tập I",
    "Đại Việt sử ký toàn thư/Tập II",
}


@dataclass
class RawPage:
    source:        str
    tap:           str
    cuon:          str
    title:         str
    url:           str
    raw_text:      str
    paragraphs:    list[str] = field(default_factory=list)
    year_mentions: list[str] = field(default_factory=list)


class DVSKTTCrawler:
    def __init__(self, delay: float = 2.0, output_dir: str = OUTPUT_DIR):
        self.delay   = delay
        self.output  = output_dir
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        os.makedirs(output_dir, exist_ok=True)

    # ── Fetch ────────────────────────────────────────────────────────────────

    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        try:
            r = self.session.get(url, timeout=20)
            r.raise_for_status()
            r.encoding = "utf-8"
            return BeautifulSoup(r.text, "lxml")
        except requests.RequestException as e:
            print(f"  [ERROR] {url}: {e}")
            return None

    # ── Discovery: tìm tất cả subpage từ trang mục lục ───────────────────────

    def discover_pages(self) -> list[dict]:
        """
        Crawl trang gốc + Tập I + Tập II để lấy toàn bộ link con.
        Trả về list dict: {url, tap, title}
        """
        index_urls = [
            BASE_URL + ROOT_PATH,
            BASE_URL + "/wiki/%C4%90%E1%BA%A1i_Vi%E1%BB%87t_s%E1%BB%AD_k%C3%BD_to%C3%A0n_th%C6%B0/T%E1%BA%ADp_I",
            BASE_URL + "/wiki/%C4%90%E1%BA%A1i_Vi%E1%BB%87t_s%E1%BB%AD_k%C3%BD_to%C3%A0n_th%C6%B0/T%E1%BA%ADp_II",
        ]

        found: dict[str, dict] = {}  # url → metadata

        for idx_url in index_urls:
            print(f"🔍 Scanning: {idx_url}")
            soup = self.fetch(idx_url)
            if not soup:
                continue
            time.sleep(1)

            tap = "Tập II" if "T%E1%BA%ADp_II" in idx_url or "Tập_II" in idx_url else "Tập I"

            content = soup.select_one("#mw-content-text")
            if not content:
                continue

            for a in content.find_all("a", href=True):
                href = a["href"]
                # Chỉ lấy link nội bộ Wikisource về bộ sách này
                if not href.startswith("/wiki/"):
                    continue
                if BOOK_PREFIX not in href:
                    continue
                if "#" in href:
                    continue

                full_url = BASE_URL + href
                # Bỏ các trang chỉ là index
                page_title = href.split("/wiki/")[-1].replace("_", " ")
                page_title = requests.utils.unquote(page_title)

                # Bỏ trang gốc và trang tập
                depth = href.count("/") - 2  # /wiki/... có 1 slash rồi
                if depth < 3:
                    continue

                if full_url not in found:
                    found[full_url] = {"url": full_url, "tap": tap, "raw_title": page_title}

        pages = list(found.values())
        print(f"   Tìm thấy {len(pages)} subpages\n")
        return pages

    # ── Parse nội dung ────────────────────────────────────────────────────────

    def parse(self, soup: BeautifulSoup) -> tuple[str, list[str]]:
        content = soup.select_one("#mw-content-text .mw-parser-output")
        if not content:
            return "", []
        for tag in content.select(
            "table.ws-noexport, .noprint, #toc, .mw-editsection, "
            "sup.reference, .reflist, .references, .ws-index, table"
        ):
            tag.decompose()
        paragraphs = []
        for p in content.find_all(["p", "li"]):
            text = re.sub(r"\s+", " ", p.get_text(separator=" ", strip=True))
            if len(text) > 40:
                paragraphs.append(text)
        return "\n\n".join(paragraphs), paragraphs

    def extract_years(self, text: str) -> list[str]:
        found = []
        for p in [
            r"\d{1,4}\s*(?:TCN|SCN|trước Tây.lịch|trước Công nguyên)",
            r"năm\s+\d{3,4}",
            r"thế\s+kỷ\s+(?:I{1,3}|IV|V{1,3}|IX|X{1,3}|XI{1,2}|XIV|XV)",
        ]:
            found.extend(re.findall(p, text, re.IGNORECASE))
        return list(set(found))

    def infer_cuon(self, url: str) -> str:
        """Đọc cuốn từ URL path."""
        parts = url.split("/")
        for part in parts:
            part_dec = requests.utils.unquote(part).replace("_", " ")
            if re.search(r"[Cc]u[ốo]n th[ứu]|[Cc]u[ốo]n\s+\d", part_dec):
                return part_dec
        return ""

    # ── Main crawl ────────────────────────────────────────────────────────────

    def crawl_all(self) -> list[RawPage]:
        pages_meta = self.discover_pages()

        if not pages_meta:
            print("❌ Không tìm được subpage nào. Kiểm tra kết nối.")
            return []

        results, failed = [], []
        print(f"📚 Bắt đầu crawl {len(pages_meta)} trang...\n")

        for meta in tqdm(pages_meta, desc="Crawling"):
            url   = meta["url"]
            tap   = meta["tap"]
            cuon  = self.infer_cuon(url)
            title = meta["raw_title"].split("/")[-1].replace("-", " ")

            soup = self.fetch(url)
            if not soup:
                failed.append(title)
                time.sleep(self.delay)
                continue

            raw_text, paragraphs = self.parse(soup)
            if not raw_text or len(paragraphs) < 2:
                failed.append(title)
                tqdm.write(f"  [SKIP] {title} — ít nội dung")
                time.sleep(self.delay)
                continue

            page = RawPage(
                source="dvsktt", tap=tap, cuon=cuon,
                title=title, url=url,
                raw_text=raw_text, paragraphs=paragraphs,
                year_mentions=self.extract_years(raw_text),
            )
            results.append(page)
            tqdm.write(f"  ✓ [{tap}] {title} — {len(paragraphs)} đoạn")
            time.sleep(self.delay)

        self._save(results)
        print(f"\n✅ Thành công : {len(results)}/{len(pages_meta)} trang")
        if failed:
            print(f"❌ Thất bại  : {len(failed)} — {', '.join(failed[:5])}")
        print(f"📊 Tổng từ   : {sum(len(p.raw_text.split()) for p in results):,}")
        return results

    def _save(self, pages: list[RawPage]):
        out_json = os.path.join(self.output, "dvsktt_raw.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in pages], f, ensure_ascii=False, indent=2)
        print(f"\n💾 JSON → {out_json}")
        out_txt = os.path.join(self.output, "dvsktt_raw.txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            for p in pages:
                f.write(f"{'='*60}\n[{p.tap}][{p.cuon}] {p.title}\n{'='*60}\n")
                f.write(p.raw_text + "\n\n")
        print(f"💾 TXT  → {out_txt}")


if __name__ == "__main__":
    DVSKTTCrawler(delay=2.0).crawl_all()