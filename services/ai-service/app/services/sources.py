SOURCE_DOCUMENT_NAMES = {
    "dvsktt": "Đại Việt sử ký toàn thư",
    "dvsktt_pdf": "Đại Việt sử ký toàn thư",
    "wiki": "Việt Nam sử lược",
    "vnsl": "Việt Nam sử lược",
}

SOURCE_DOCUMENT_URLS = {
    "Đại Việt sử ký toàn thư": "https://vi.wikisource.org/wiki/Đại_Việt_sử_ký_toàn_thư",
    "Việt Nam sử lược": "https://vi.wikisource.org/wiki/Việt_Nam_sử_lược",
}


def source_references(chunks: list[dict]) -> list[dict]:
    """Return one display-ready reference for each retrieved document."""
    references: list[dict] = []
    references_by_key: dict[str, dict] = {}

    for chunk in chunks:
        raw_source = str(chunk.get("source") or "").strip()
        document = SOURCE_DOCUMENT_NAMES.get(raw_source.lower(), raw_source)
        if not document:
            continue

        key = document.casefold()
        explicit_url = str(chunk.get("url") or "").strip() or None
        fallback_url = SOURCE_DOCUMENT_URLS.get(document)
        url = explicit_url or fallback_url
        existing = references_by_key.get(key)
        if existing:
            if explicit_url and existing["url"] in (None, fallback_url):
                existing["url"] = explicit_url
            continue

        reference = {
            "document": document,
            "url": url,
        }
        references_by_key[key] = reference
        references.append(reference)

    return references
