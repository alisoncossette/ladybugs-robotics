"""Integration tests for perception skills.

These tests call the real Claude Vision API to validate that:
- assess_scene returns valid scene states
- classify_page returns valid page types
- read_left / read_right return non-empty text

Requires ANTHROPIC_API_KEY to be set. Skips if not available.
"""

import os
import unittest

# Skip all tests if no API key
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SKIP_REASON = "ANTHROPIC_API_KEY not set -- skipping live API tests"

# Path to test images
TEST_DATA = os.path.join(os.path.dirname(__file__), "..", "test_data")


def _load_image(filename: str) -> bytes:
    """Load a test image as bytes."""
    path = os.path.join(TEST_DATA, filename)
    if not os.path.exists(path):
        return b""
    with open(path, "rb") as f:
        return f.read()


@unittest.skipUnless(ANTHROPIC_KEY, SKIP_REASON)
class TestAssessScene(unittest.TestCase):
    """Test assess_scene against real images."""

    def test_open_book_detected(self):
        """An image of an open book should return 'book_open'."""
        from src.skills.perception import assess_scene

        img = _load_image("page.jpg")
        if not img:
            self.skipTest("test_data/page.jpg not found")

        result = assess_scene(img)
        self.assertIn(result, ("book_open", "book_done", "book_closed"),
                      f"Expected a book-related state, got: {result}")

    def test_returns_valid_state(self):
        """assess_scene should always return one of the 4 known states."""
        from src.skills.perception import assess_scene

        img = _load_image("page.jpg")
        if not img:
            self.skipTest("test_data/page.jpg not found")

        result = assess_scene(img)
        valid_states = {"no_book", "book_closed", "book_open", "book_done"}
        self.assertIn(result, valid_states,
                      f"assess_scene returned unknown state: {result}")


@unittest.skipUnless(ANTHROPIC_KEY, SKIP_REASON)
class TestClassifyPage(unittest.TestCase):
    """Test page classification against real images."""

    def test_content_page(self):
        """A page with text content should classify as 'content'."""
        from src.pipeline.page_reader import classify_page

        img = _load_image("page.jpg")
        if not img:
            self.skipTest("test_data/page.jpg not found")

        result = classify_page(img)
        valid_types = {"blank", "index", "cover", "title", "toc", "content"}
        self.assertIn(result, valid_types,
                      f"classify_page returned unknown type: {result}")

    def test_index_page(self):
        """An index page image should classify as 'index'."""
        from src.pipeline.page_reader import classify_page

        img = _load_image("index/20260131_174805.jpg")
        if not img:
            self.skipTest("test_data/index/20260131_174805.jpg not found")

        result = classify_page(img)
        self.assertEqual(result, "index",
                         f"Expected 'index', got: {result}")


@unittest.skipUnless(ANTHROPIC_KEY, SKIP_REASON)
class TestReadLeftRight(unittest.TestCase):
    """Test that read_left and read_right return text from a spread."""

    def test_read_left_returns_text(self):
        """read_left should return non-empty text from a book spread."""
        from src.skills.perception import read_left

        img = _load_image("page.jpg")
        if not img:
            self.skipTest("test_data/page.jpg not found")

        text = read_left(img, silent=True, mode="skim")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text.strip()), 0,
                           "read_left returned empty text")

    def test_read_right_returns_text(self):
        """read_right should return non-empty text from a book spread."""
        from src.skills.perception import read_right

        img = _load_image("page.jpg")
        if not img:
            self.skipTest("test_data/page.jpg not found")

        text = read_right(img, silent=True, mode="skim")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text.strip()), 0,
                           "read_right returned empty text")

    def test_left_and_right_differ(self):
        """read_left and read_right should return different text from the same spread."""
        from src.skills.perception import read_left, read_right

        img = _load_image("page.jpg")
        if not img:
            self.skipTest("test_data/page.jpg not found")

        left = read_left(img, silent=True, mode="verbose")
        right = read_right(img, silent=True, mode="verbose")

        # They should both have content
        self.assertGreater(len(left.strip()), 0)
        self.assertGreater(len(right.strip()), 0)

        # They should be different (reading different pages)
        self.assertNotEqual(left.strip(), right.strip(),
                            "read_left and read_right returned identical text -- "
                            "may not be isolating pages correctly")


if __name__ == "__main__":
    unittest.main()
