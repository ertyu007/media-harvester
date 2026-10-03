import os
import shutil
import tempfile
import unittest
from core.models import MediaItem, MediaType, ScrapeResult
from core.organizer import (
    sanitize_filename,
    resolve_collision,
    MediaOrganizer
)

class TestOrganizer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("invalid:file*name?.jpg"), "invalid_file_name.jpg")
        self.assertEqual(sanitize_filename("spaces   and___underscores.png"), "spaces_and_underscores.png")
        self.assertEqual(sanitize_filename(""), "media")
        
        long_name = "a" * 200 + ".jpg"
        sanitized = sanitize_filename(long_name, max_length=50)
        self.assertEqual(len(sanitized), 54) # 50 chars stem + 4 chars .jpg

    def test_resolve_collision(self):
        file_path = os.path.join(self.test_dir, "test.jpg")
        # File doesn't exist yet -> returns path as-is
        self.assertEqual(resolve_collision(file_path), file_path)

        # Create file on disk
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("content")

        expected_2 = os.path.join(self.test_dir, "test_2.jpg")
        self.assertEqual(resolve_collision(file_path), expected_2)

        # Create test_2.jpg on disk
        with open(expected_2, "w", encoding="utf-8") as f:
            f.write("content 2")

        expected_3 = os.path.join(self.test_dir, "test_3.jpg")
        self.assertEqual(resolve_collision(file_path), expected_3)

    def test_create_destination_structure(self):
        organizer = MediaOrganizer(base_output_dir=self.test_dir)
        target_dir = organizer.create_destination_structure("https://example.com/gallery", custom_folder_name="custom_art")
        self.assertEqual(target_dir, os.path.join(self.test_dir, "custom_art"))

        for m_type in MediaType:
            sub = os.path.join(target_dir, m_type.value)
            self.assertTrue(os.path.isdir(sub))

    def test_get_destination_filepath_in_memory_dedup(self):
        organizer = MediaOrganizer(base_output_dir=self.test_dir)
        target_dir = organizer.create_destination_structure("https://example.com")

        item1 = MediaItem(
            url="https://example.com/img1/logo.png",
            media_type=MediaType.IMAGE,
            source_tag="img",
            original_filename="logo.png",
            extension=".png"
        )
        item2 = MediaItem(
            url="https://example.com/img2/logo.png",
            media_type=MediaType.IMAGE,
            source_tag="img",
            original_filename="logo.png",
            extension=".png"
        )

        p1 = organizer.get_destination_filepath(target_dir, item1, index=1, prefix_index=False)
        p2 = organizer.get_destination_filepath(target_dir, item2, index=2, prefix_index=False)

        self.assertTrue(p1.endswith("logo.png"))
        self.assertTrue(p2.endswith("logo_2.png"))

    def test_generate_manifest_and_summary(self):
        organizer = MediaOrganizer(base_output_dir=self.test_dir)
        target_dir = organizer.create_destination_structure("https://example.com")

        item = MediaItem(
            url="https://example.com/photo.jpg",
            media_type=MediaType.IMAGE,
            source_tag="img",
            original_filename="photo.jpg",
            extension=".jpg",
            download_status="success",
            saved_path=os.path.join(target_dir, "images", "photo.jpg"),
            file_size=10240
        )

        scrape_res = ScrapeResult(source_url="https://example.com", title="Test Page", items=[item], stats={"images": 1})
        organizer.write_manifest(target_dir, scrape_res, [item])

        manifest_path = os.path.join(target_dir, "manifest.json")
        summary_path = os.path.join(target_dir, "summary.md")

        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(summary_path))

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = f.read()
            self.assertIn("https://example.com/photo.jpg", data)

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = f.read()
            self.assertIn("Media Harvest Report", summary)

if __name__ == "__main__":
    unittest.main()
