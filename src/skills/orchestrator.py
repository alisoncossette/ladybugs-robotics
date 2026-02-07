"""Skill orchestrator -- assess_scene-driven state machine.

The orchestrator runs a perception-action loop:
    1. assess_scene → determine current state of the workspace
    2. Execute the appropriate skill(s) based on state
    3. Repeat until done

State transitions:
    no_book     → done (nothing to do)
    book_closed → open_book → assess_scene
    book_open   → classify → read_left → read_right → turn_page → assess_scene
    book_done   → close_book → done
"""

from src.pipeline.camera import CameraStream
from src.pipeline.page_reader import SKIP_TYPES, classify_page
from src.skills.motor import MOTOR_SKILLS
from src.skills.perception import assess_scene, read_left, read_right


class BookReaderOrchestrator:
    """Autonomous book reading state machine.

    Uses assess_scene as the router to decide which skill to execute next.
    Motor skills drive the arm via Solo CLI. Perception skills use the
    camera and Claude Vision to read pages and understand the workspace.
    """

    def __init__(self, camera_stream: CameraStream, silent: bool = False,
                 mode: str = "verbose"):
        self.stream = camera_stream
        self.silent = silent
        self.mode = mode
        self.spread_count = 0

    def run(self) -> None:
        """Run the autonomous reading loop."""
        print("=" * 50)
        print("  LADYBUGS BOOK READER -- AUTONOMOUS MODE")
        print("=" * 50)
        print()
        print(f"Speech: {'off' if self.silent else 'on'}")
        print(f"Mode:   {self.mode}")
        print("-" * 50)

        while True:
            # Step 1: Assess the scene
            img = self.stream.grab()
            scene_state = assess_scene(img)
            print(f"\n[assess_scene] → {scene_state}")

            if scene_state == "no_book":
                print("No book detected. Done.")
                break

            elif scene_state == "book_closed":
                print("Book is closed. Opening...")
                MOTOR_SKILLS["open_book"].execute()

            elif scene_state == "book_open":
                self._read_spread()

            elif scene_state == "book_done":
                print("Last page reached. Closing book...")
                MOTOR_SKILLS["close_book"].execute()
                print("Book reading complete.")
                break

        print("\n" + "=" * 50)
        print("  SESSION COMPLETE")
        print("=" * 50)

    def _read_spread(self) -> None:
        """Read the current two-page spread, then turn the page."""
        self.spread_count += 1
        print(f"\n--- Spread {self.spread_count} ---")

        # Grab a fresh frame for reading
        img = self.stream.grab()

        # Classify before committing to a full read
        page_type = classify_page(img)
        print(f"[classify] → {page_type}")

        if page_type in SKIP_TYPES:
            print(f"Skipping {page_type} page.")
        else:
            # Read left page, then right page
            print("\n[read_left]")
            read_left(img, silent=self.silent, mode=self.mode)

            print("\n[read_right]")
            read_right(img, silent=self.silent, mode=self.mode)

        # Turn to the next page
        print("\n[turn_page]")
        MOTOR_SKILLS["turn_page"].execute()

        print(f"--- End of spread {self.spread_count} ---")
