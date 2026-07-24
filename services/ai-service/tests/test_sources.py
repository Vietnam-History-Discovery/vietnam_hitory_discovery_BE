import unittest

from app.services.sources import source_references


class SourceReferencesTest(unittest.TestCase):
    def test_maps_and_deduplicates_document_sources(self):
        chunks = [
            {"source": "dvsktt_pdf", "url": ""},
            {"source": "dvsktt", "url": "https://example.test/first"},
            {"source": "wiki", "url": ""},
        ]

        self.assertEqual([
            {
                "document": "Đại Việt sử ký toàn thư",
                "url": "https://example.test/first",
            },
            {
                "document": "Việt Nam sử lược",
                "url": "https://vi.wikisource.org/wiki/Việt_Nam_sử_lược",
            },
        ], source_references(chunks))

    def test_preserves_an_unknown_human_readable_source(self):
        self.assertEqual(
            [{"document": "Khâm định Việt sử Thông giám cương mục", "url": None}],
            source_references([{"source": "Khâm định Việt sử Thông giám cương mục"}]),
        )

    def test_ignores_chunks_without_a_source(self):
        self.assertEqual([], source_references([{"title": "Unknown"}, {}]))


if __name__ == "__main__":
    unittest.main()
