import unittest
from core.models import MediaType
from core.extractor import (
    detect_media_type,
    is_tracking_url,
    extract_best_from_srcset,
    clean_media_filename,
    enhance_highres_url,
    MediaExtractor
)

class TestExtractor(unittest.TestCase):
    def test_detect_media_type_extensions(self):
        # Image
        m_type, ext = detect_media_type("https://example.com/photo.JPG")
        self.assertEqual(m_type, MediaType.IMAGE)
        self.assertEqual(ext, ".jpg")

        # Video
        m_type, ext = detect_media_type("https://example.com/clip.mp4?token=123")
        self.assertEqual(m_type, MediaType.VIDEO)
        self.assertEqual(ext, ".mp4")

        # Audio
        m_type, ext = detect_media_type("https://example.com/music.mp3")
        self.assertEqual(m_type, MediaType.AUDIO)
        self.assertEqual(ext, ".mp3")

        # Document
        m_type, ext = detect_media_type("https://example.com/archive.zip")
        self.assertEqual(m_type, MediaType.DOCUMENT)
        self.assertEqual(ext, ".zip")

        # Non-media web page
        m_type, ext = detect_media_type("https://example.com/about.html")
        self.assertIsNone(m_type)
        self.assertEqual(ext, "")

    def test_detect_media_type_tag_inference(self):
        m_type, ext = detect_media_type("https://example.com/api/render?id=99", tag_name="img")
        self.assertEqual(m_type, MediaType.IMAGE)
        self.assertTrue(ext in [".jpg", ".png", ".webp"])

        m_type, ext = detect_media_type("https://example.com/stream/feed", tag_name="video")
        self.assertEqual(m_type, MediaType.VIDEO)
        self.assertEqual(ext, ".mp4")

    def test_tracking_urls(self):
        self.assertTrue(is_tracking_url("https://www.google-analytics.com/collect"))
        self.assertTrue(is_tracking_url("https://connect.facebook.net/en_US/fbevents.js"))
        self.assertFalse(is_tracking_url("https://example.com/images/hero.png"))

    def test_extract_best_from_srcset(self):
        base = "https://example.com/blog/"
        srcset = "thumb-300w.jpg 300w, medium-768w.jpg 768w, large-1200w.jpg 1200w"
        best = extract_best_from_srcset(srcset, base)
        self.assertEqual(best, "https://example.com/blog/large-1200w.jpg")

        # Pixel density descriptors
        srcset_x = "pic1.png 1x, pic2.png 2x"
        best_x = extract_best_from_srcset(srcset_x, base)
        self.assertEqual(best_x, "https://example.com/blog/pic2.png")

    def test_clean_media_filename_and_enhance(self):
        # Strip query parameters
        clean1 = clean_media_filename("https://example.com/photos/landscape.jpg?size=large&v=2")
        self.assertEqual(clean1, "landscape.jpg")

        # High-res enhancement strips WordPress thumbnail dimension suffix
        enhanced = enhance_highres_url("https://example.com/uploads/banner-1920x1080.png")
        self.assertEqual(enhanced, "https://example.com/uploads/banner.png")
        clean2 = clean_media_filename(enhanced)
        self.assertEqual(clean2, "banner.png")

    def test_extract_from_html(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Gallery</title></head>
        <body>
            <div style="background-image: url('/assets/bg.webp');">
                <img src="/images/cat.jpg" alt="Cute Cat" />
                <picture>
                    <source srcset="/images/dog-large.png 2x, /images/dog-small.png 1x" type="image/png">
                    <img src="/images/dog-fallback.png" alt="Dog">
                </picture>
                <video src="/videos/intro.mp4"></video>
                <audio src="/sounds/bell.mp3"></audio>
                <a href="/docs/guide.pdf">Download PDF</a>
            </div>
        </body>
        </html>
        """
        extractor = MediaExtractor()
        result = extractor.extract_from_html(html, "https://example.com/gallery")
        self.assertEqual(result.title, "Test Gallery")
        
        urls = [item.url for item in result.items]
        self.assertIn("https://example.com/assets/bg.webp", urls)
        self.assertIn("https://example.com/images/cat.jpg", urls)
        self.assertIn("https://example.com/images/dog-large.png", urls)
        self.assertIn("https://example.com/videos/intro.mp4", urls)
        self.assertIn("https://example.com/sounds/bell.mp3", urls)
        self.assertIn("https://example.com/docs/guide.pdf", urls)

    def test_extract_img_data_url(self):
        html = '<img class="_images" src="placeholder.png" data-url="https://example.com/ep1/1.jpg">'
        extractor = MediaExtractor()
        result = extractor.extract_from_html(html, "https://example.com")
        self.assertIn("https://example.com/ep1/1.jpg", [i.url for i in result.items])

    def test_extract_internal_links_keeps_query(self):
        html = '<a href="/viewer?episode_no=3">ep3</a><a href="https://other.com/x">out</a><a href="/page#frag">p</a>'
        extractor = MediaExtractor()
        links = extractor.extract_internal_links(html, "https://example.com")
        self.assertIn("https://example.com/viewer?episode_no=3", links)
        self.assertIn("https://example.com/page", links)
        self.assertNotIn("https://other.com/x", links)

    def test_extract_recursive_link_pattern(self):
        class FakeExtractor(MediaExtractor):
            pages = {
                "https://example.com": ('<a href="/viewer?episode_no=1">1</a><a href="/about">a</a>', "https://example.com"),
                "https://example.com/viewer?episode_no=1": ('<img src="/1.jpg">', "https://example.com/viewer?episode_no=1"),
                "https://example.com/about": ('<img src="/about.jpg">', "https://example.com/about"),
            }
            def fetch_html(self, url):
                html, final = self.pages[url]
                return final, html, None
        extractor = FakeExtractor()
        result = extractor.extract_recursive("https://example.com", depth=1, link_pattern=r"viewer")
        urls = [i.url for i in result.items]
        self.assertIn("https://example.com/1.jpg", urls)
        self.assertNotIn("https://example.com/about.jpg", urls)

if __name__ == "__main__":
    unittest.main()
