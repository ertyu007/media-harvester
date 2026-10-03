import os
import shutil
import tempfile
import hashlib
import unittest
from core.downloader import (
    resolve_extension_from_mime,
    compute_file_hash,
    is_duplicate_content,
    MIME_TO_EXT
)

class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_resolve_extension_from_mime(self):
        # Valid image match
        self.assertEqual(resolve_extension_from_mime("image/jpeg", ".jpg"), ".jpg")
        self.assertEqual(resolve_extension_from_mime("image/png; charset=utf-8", ".jpg"), ".png")
        self.assertEqual(resolve_extension_from_mime("image/webp", ".unknown"), ".webp")

        # Video / Audio / PDF
        self.assertEqual(resolve_extension_from_mime("video/mp4", ".mp4"), ".mp4")
        self.assertEqual(resolve_extension_from_mime("audio/mpeg", ".mp3"), ".mp3")
        self.assertEqual(resolve_extension_from_mime("application/pdf", ".pdf"), ".pdf")

        # Application/octet-stream -> preserve current extension
        self.assertEqual(resolve_extension_from_mime("application/octet-stream", ".bin"), ".bin")

        # Non-media (HTML/JSON/JS) -> rejected (returns None)
        self.assertIsNone(resolve_extension_from_mime("text/html", ".jpg"))
        self.assertIsNone(resolve_extension_from_mime("application/json", ".png"))
        self.assertIsNone(resolve_extension_from_mime("application/javascript", ".jpg"))

    def test_compute_file_hash(self):
        file_path = os.path.join(self.test_dir, "sample.bin")
        content = b"MediaHarvesterTestBinaryData"
        with open(file_path, "wb") as f:
            f.write(content)

        expected_sha256 = hashlib.sha256(content).hexdigest()
        actual_hash = compute_file_hash(file_path)
        self.assertEqual(actual_hash, expected_sha256)

    def test_is_duplicate_content(self):
        file1 = os.path.join(self.test_dir, "file1.png")
        file2 = os.path.join(self.test_dir, "file2.png")
        content = b"SameContentForDedup"

        with open(file1, "wb") as f:
            f.write(content)

        seen_hashes = set()
        # First file is not duplicate
        self.assertFalse(is_duplicate_content(file1, seen_hashes))
        
        # Second file with same content is duplicate
        with open(file2, "wb") as f:
            f.write(content)
        self.assertTrue(is_duplicate_content(file2, seen_hashes))

if __name__ == "__main__":
    unittest.main()
