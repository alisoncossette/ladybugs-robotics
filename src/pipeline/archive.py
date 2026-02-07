"""Archive utility -- save screenshots and extracted text from reading sessions.

When --archive is enabled, each spread's camera frame and read text are saved
to a timestamped session directory:

    archive/
      2026-02-07_143022/
        spread_001_frame.jpg
        spread_001_left.txt
        spread_001_right.txt
        spread_001_meta.txt       (page type, scene state)
        spread_002_frame.jpg
        ...
        session.txt               (full concatenated text of the book)
"""

import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)


class Archive:
    """Saves frames and text to disk during a reading session."""

    def __init__(self, base_dir: str = "archive"):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.session_dir = os.path.join(base_dir, timestamp)
        self._full_text: list[str] = []

    def start(self) -> None:
        """Create the session directory."""
        os.makedirs(self.session_dir, exist_ok=True)
        log.info("Archive: saving to %s", self.session_dir)

    def save_spread(self, spread_num: int, frame: bytes,
                    page_type: str, scene_state: str,
                    left_text: str = "", right_text: str = "") -> None:
        """Save a spread's frame, text, and metadata."""
        prefix = f"spread_{spread_num:03d}"

        # Save frame
        frame_path = os.path.join(self.session_dir, f"{prefix}_frame.jpg")
        with open(frame_path, "wb") as f:
            f.write(frame)

        # Save left page text
        if left_text:
            left_path = os.path.join(self.session_dir, f"{prefix}_left.txt")
            with open(left_path, "w", encoding="utf-8") as f:
                f.write(left_text)
            self._full_text.append(left_text)

        # Save right page text
        if right_text:
            right_path = os.path.join(self.session_dir, f"{prefix}_right.txt")
            with open(right_path, "w", encoding="utf-8") as f:
                f.write(right_text)
            self._full_text.append(right_text)

        # Save metadata
        meta_path = os.path.join(self.session_dir, f"{prefix}_meta.txt")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"scene_state: {scene_state}\n")
            f.write(f"page_type: {page_type}\n")
            f.write(f"has_left: {bool(left_text)}\n")
            f.write(f"has_right: {bool(right_text)}\n")

        log.info("Archive: saved %s (type=%s, left=%d chars, right=%d chars)",
                 prefix, page_type, len(left_text), len(right_text))

    def save_single(self, page_num: int, frame: bytes,
                    page_type: str, text: str = "") -> None:
        """Save a single page's frame and text (for folder/manual modes)."""
        prefix = f"page_{page_num:03d}"

        frame_path = os.path.join(self.session_dir, f"{prefix}_frame.jpg")
        with open(frame_path, "wb") as f:
            f.write(frame)

        if text:
            text_path = os.path.join(self.session_dir, f"{prefix}_text.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)
            self._full_text.append(text)

        meta_path = os.path.join(self.session_dir, f"{prefix}_meta.txt")
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"page_type: {page_type}\n")
            f.write(f"has_text: {bool(text)}\n")

        log.info("Archive: saved %s (type=%s, %d chars)",
                 prefix, page_type, len(text))

    def finalize(self) -> str:
        """Write the full concatenated session text and return the session path."""
        if self._full_text:
            session_path = os.path.join(self.session_dir, "session.txt")
            with open(session_path, "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(self._full_text))
            log.info("Archive: wrote session.txt (%d sections, %d total chars)",
                     len(self._full_text),
                     sum(len(t) for t in self._full_text))

        log.info("Archive: session saved to %s", self.session_dir)
        return self.session_dir
