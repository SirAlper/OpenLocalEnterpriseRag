import os
import tempfile
import unittest
from src.rag.document_loader import DocumentLoader


class TestDocumentLoader(unittest.TestCase):
    """Tests for document loading, header extraction, and chunking."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.loader = DocumentLoader(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_document_header_english(self):
        content = """DOCUMENT: Information Security Policy
CODE: SEC-POL-04
Date: 2026-01-01

All employees must follow the security guidelines."""
        header = DocumentLoader._extract_document_header(content)
        self.assertEqual(header, "[Document: Information Security Policy | CODE: SEC-POL-04]")

    def test_extract_document_header_turkish(self):
        content = """DOKÜMAN: Yıllık İzin Prosedürü
KOD: IK-PRO-12
Tarih: 2026-01-01

Tüm personelin izin talepleri İK portalı üzerinden alınır."""
        header = DocumentLoader._extract_document_header(content)
        self.assertEqual(header, "[Document: Yıllık İzin Prosedürü | CODE: IK-PRO-12]")

    def test_extract_document_header_title_only(self):
        content = """DOCUMENT: Code of Conduct
Some other text here."""
        header = DocumentLoader._extract_document_header(content)
        self.assertEqual(header, "[Document: Code of Conduct]")

    def test_extract_document_header_none(self):
        content = "Just plain text without document keyword."
        header = DocumentLoader._extract_document_header(content)
        self.assertEqual(header, "")

    def test_load_and_chunk_txt_file(self):
        sample_file = os.path.join(self.temp_dir.name, "sample_policy.txt")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("""DOCUMENT: Enterprise Data Retention
CODE: DTR-01

Employees must retain records for a minimum period of 5 years.
Archived documents must be encrypted at rest and in transit.""")

        chunks, ids, metas = self.loader.load_and_chunk_file(sample_file)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("[Document: Enterprise Data Retention | CODE: DTR-01]", chunks[0])
        self.assertEqual(metas[0]["source"], "sample_policy.txt")

    def test_unsupported_file_extension(self):
        bad_file = os.path.join(self.temp_dir.name, "script.sh")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\necho hello")

        chunks, ids, metas = self.loader.load_and_chunk_file(bad_file)
        self.assertEqual(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()
