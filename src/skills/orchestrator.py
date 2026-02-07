"""Skill orchestrator -- assess_scene-driven state machine.

The orchestrator runs a perception-action loop:
    1. assess_scene -> determine current state of the workspace
    2. Execute the appropriate skill(s) based on state
    3. Repeat until done

State transitions:
    no_book     -> done (nothing to do)
    book_closed -> open_book -> assess_scene
    book_open   -> classify -> read_left -> read_right -> turn_page -> assess_scene
    book_done   -> close_book -> done
"""

import logging

from src.pipeline.camera import frame_hash
from src.pipeline.page_reader import SKIP_TYPES, classify_page
from src.skills.motor import MOTOR_SKILLS, _build_motor_skills
from src.skills.perception import assess_scene, read_left, read_right

log = logging.getLogger(__name__)

# Maximum consecutive same-page detections before giving up
MAX_SAME_PAGE_RETRIES = 2


class BookReaderOrchestrator:
    """Autonomous book reading state machine.

    Uses assess_scene as the router to decide which skill to execute next.
    Motor skills drive the arm via Solo CLI. Perception skills use the
    camera and Claude Vision to read pages and understand the workspace.
    """

    def __init__(self, image_source, silent: bool = False,
                 mode: str = "verbose", dry_run: bool = False):
        self.source = image_source
        self.silent = silent
        self.mode = mode
        self.dry_run = dry_run
        self.spread_count = 0
        self._last_frame_hash: str | None = None
        self._motor = _build_motor_skills(dry_run=dry_run) if dry_run else MOTOR_SKILLS

    def run(self) -> None:
        """Run the autonomous reading loop."""
        label = "DRY-RUN MODE" if self.dry_run else "AUTONOMOUS MODE"
        log.info("=" * 50)
        log.info("  LADYBUGS BOOK READER -- %s", label)
        log.info("=" * 50)
        log.info("Speech: %s", "off" if self.silent else "on")
        log.info("Mode:   %s", self.mode)
        log.info("-" * 50)

        while True:
            # Step 1: Assess the scene
            img = self.source.grab()
            scene_state = assess_scene(img)
            log.info("[assess_scene] -> %s", scene_state)

            if scene_state == "no_book":
                log.info("No book detected. Done.")
                break

            elif scene_state == "book_closed":
                log.info("Book is closed. Opening...")
                success = self._motor["open_book"].execute()
                if not success:
                    log.error("open_book failed. Stopping.")
                    break

            elif scene_state == "book_open":
                self._read_spread()

            elif scene_state == "book_done":
                log.info("Last page reached. Closing book...")
                self._motor["close_book"].execute()
                log.info("Book reading complete.")
                break

        log.info("=" * 50)
        log.info("  SESSION COMPLETE")
        log.info("=" * 50)

    def _read_spread(self) -> None:
        """Read the current two-page spread, then turn the page."""
        self.spread_count += 1
        log.info("--- Spread %d ---", self.spread_count)

        # Grab a fresh frame for reading
        img = self.source.grab()

        # Classify before committing to a full read
        page_type = classify_page(img)
        log.info("[classify] -> %s", page_type)

        if page_type in SKIP_TYPES:
            log.info("Skipping %s page.", page_type)
        else:
            # Read left page, then right page
            log.info("[read_left]")
            read_left(img, silent=self.silent, mode=self.mode)

            log.info("[read_right]")
            read_right(img, silent=self.silent, mode=self.mode)

        # Turn to the next page
        self._turn_with_verification()

        log.info("--- End of spread %d ---", self.spread_count)

    def _turn_with_verification(self) -> None:
        """Turn the page and verify via frame hash that it actually changed.

        If the frame looks the same after turning, retry up to
        MAX_SAME_PAGE_RETRIES times before moving on.
        """
        # Snapshot before turning
        pre_img = self.source.grab()
        pre_hash = frame_hash(pre_img)

        for attempt in range(1, MAX_SAME_PAGE_RETRIES + 2):
            log.info("[turn_page] attempt %d", attempt)
            success = self._motor["turn_page"].execute()

            if not success:
                log.error("turn_page motor skill failed.")
                return

            # Dry-run: no real page change to detect, just proceed
            if self.dry_run:
                return

            # Check if the page actually changed
            post_img = self.source.grab()
            post_hash = frame_hash(post_img)

            if post_hash != pre_hash:
                log.info("Page change detected.")
                self._last_frame_hash = post_hash
                return

            if attempt <= MAX_SAME_PAGE_RETRIES:
                log.warning("Same page detected (hash unchanged). Retrying turn...")
            else:
                log.warning("Page still unchanged after %d retries. Moving on.",
                            MAX_SAME_PAGE_RETRIES)
                self._last_frame_hash = post_hash
                return
