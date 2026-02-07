"""Ladybugs Robotics -- Book Reader

SO-101 robotic arm opens a book, reads pages aloud, and turns pages.

Six skills work together in an assess_scene-driven loop:
    Motor skills  : open_book, close_book, turn_page (Solo CLI + ACT policies)
    Perception    : assess_scene, read_left, read_right (camera + Claude Vision)

Autonomous flow:
    1. assess_scene -> determine workspace state
    2. Execute skill(s) based on state (open, read, turn, close)
    3. Repeat until done

Usage:
    # Autonomous mode -- full skill loop with arm
    python main.py

    # Dry-run mode -- walk state machine with test images, no hardware
    python main.py --dry-run --folder test_data/ --silent

    # Manual mode -- press Enter to trigger each cycle (debugging)
    python main.py --manual

    # Test with a saved image
    python main.py --image test_data/page.jpg --mode verbose

    # Test with a folder of page images (reads in filename order)
    python main.py --folder test_data/

    # Silent mode (text only, no speech)
    python main.py --silent
"""

import argparse
import glob
import logging
import os
import sys

from src.config import (
    ANTHROPIC_API_KEY,
    ARM_CAMERA_INDEX,
    DEFAULT_CAMERA,
    TABLE_CAMERA_INDEX,
    setup_logging,
    validate_config,
)
from src.pipeline.page_reader import (
    READ_TYPES,
    SKIP_TYPES,
    classify_page,
    read_from_camera,
    read_from_file,
    read_page,
    read_page_and_speak,
)

log = logging.getLogger(__name__)


def _read_image_bytes(image_path: str, silent: bool, mode: str) -> tuple[str, str]:
    """Classify a page and read it if appropriate. Returns (page_type, text)."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    page_type = classify_page(image_bytes)

    if page_type in SKIP_TYPES:
        return page_type, ""

    if silent:
        text = read_page(image_bytes, mode=mode)
    else:
        text = read_page_and_speak(image_bytes, silent=False, mode=mode)

    return page_type, text


def run_folder(folder_path: str, silent: bool, mode: str) -> None:
    """Read all images in a folder in sorted order, like turning pages."""
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    files = []
    for pat in patterns:
        files.extend(glob.glob(os.path.join(folder_path, pat)))
    files.sort()

    if not files:
        log.error("No images found in %s", folder_path)
        return

    log.info("=" * 50)
    log.info("  LADYBUGS BOOK READER")
    log.info("=" * 50)
    log.info("Pages found: %d", len(files))
    log.info("Mode:   %s", mode)
    log.info("Speech: %s", "off" if silent else "on")
    log.info("-" * 50)

    for i, filepath in enumerate(files, 1):
        filename = os.path.basename(filepath)
        log.info("--- Page %d/%d: %s ---", i, len(files), filename)

        page_type, text = _read_image_bytes(filepath, silent, mode)

        if page_type in SKIP_TYPES:
            log.info("[%s page -- skipping]", page_type)
            continue

        log.info("[%s]", page_type)
        if silent:
            print(text)

        log.info("--- End of page %d ---", i)

    log.info("=" * 50)
    log.info("  DONE")
    log.info("=" * 50)


def run_single(image_path: str, silent: bool, mode: str) -> None:
    """Read a single image file with classification."""
    log.info("Reading from image: %s", image_path)

    page_type, text = _read_image_bytes(image_path, silent, mode)

    if page_type in SKIP_TYPES:
        log.info("[%s page -- would skip in auto mode]", page_type)
        return

    log.info("[%s]", page_type)
    if silent:
        print(text)


def _process_frame(img: bytes, page_num: int, side: str,
                    silent: bool, mode: str) -> str:
    """Classify and read a single frame. Returns the page type."""
    page_type = classify_page(img)
    label = f"Page {page_num} ({side})" if side else f"Page {page_num}"
    log.info("[%s: %s]", label, page_type)

    if page_type in SKIP_TYPES:
        log.info("  Skipping %s page...", page_type)
        return page_type

    if silent:
        text = read_page(img, mode=mode)
        print(text)
    else:
        read_page_and_speak(img, silent=False, mode=mode)

    return page_type


def run_manual(camera_index: int, silent: bool, mode: str) -> None:
    """Manual mode -- press Enter to trigger each read cycle.

    Useful for debugging without the arm connected.
    """
    from src.pipeline.camera import CameraStream

    page_num = 0

    log.info("=" * 50)
    log.info("  LADYBUGS BOOK READER -- MANUAL MODE")
    log.info("=" * 50)
    log.info("Camera index: %d", camera_index)
    log.info("Speech: %s", "off" if silent else "on")
    log.info("Mode:   %s", mode)
    print("\nPress Enter after each page turn. Type 'q' to quit.")
    log.info("-" * 50)

    with CameraStream(camera_index) as stream:
        log.info("Camera stream open.")

        while True:
            try:
                user_input = input(
                    "\n[Enter] Read spread  |  [q] Quit > "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nDone.")
                break

            if user_input == "q":
                print("Done.")
                break

            page_num += 1
            log.info("--- Spread %d ---", page_num)

            img = stream.grab()
            _process_frame(img, page_num, "", silent, mode)

            log.info("--- End of spread %d ---", page_num)


def run_autonomous(camera_index: int, silent: bool, mode: str) -> None:
    """Autonomous mode -- full skill loop driven by assess_scene."""
    from src.pipeline.camera import CameraStream
    from src.skills.orchestrator import BookReaderOrchestrator

    with CameraStream(camera_index) as stream:
        orchestrator = BookReaderOrchestrator(stream, silent=silent, mode=mode)
        orchestrator.run()


def run_dry_run(folder_path: str, silent: bool, mode: str) -> None:
    """Dry-run mode -- walk the full orchestrator state machine using test images.

    Motor skills are simulated. Perception skills (assess_scene, read_left,
    read_right) run against the images for real via Claude Vision.
    """
    from src.pipeline.camera import FolderImageSource
    from src.skills.orchestrator import BookReaderOrchestrator

    with FolderImageSource(folder_path) as source:
        orchestrator = BookReaderOrchestrator(
            source, silent=silent, mode=mode, dry_run=True
        )
        orchestrator.run()


def main():
    parser = argparse.ArgumentParser(
        description="Ladybugs Book Reader: SO-101 arm reads a book aloud"
    )
    parser.add_argument(
        "--camera",
        choices=["arm", "table", "both"],
        default=DEFAULT_CAMERA,
        help="Which camera to use (default: table)",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to a single image file",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Path to a folder of page images (reads all in order)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Text output only, no speech",
    )
    parser.add_argument(
        "--mode",
        choices=["verbose", "skim"],
        default="skim",
        help="verbose = read everything, skim = titles/headings only (default: skim)",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Manual mode: press Enter to trigger each cycle (no arm needed)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode: simulate motor skills, use --folder images for perception",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Override log level (default: INFO)",
    )
    args = parser.parse_args()

    # Initialize logging
    setup_logging(args.log_level or "INFO")

    # Validate config before doing anything
    validate_config(silent=args.silent, dry_run=args.dry_run)

    if args.dry_run:
        if not args.folder:
            log.error("--dry-run requires --folder to provide test images.")
            sys.exit(1)
        run_dry_run(args.folder, args.silent, args.mode)
    elif args.folder and not args.dry_run:
        run_folder(args.folder, args.silent, args.mode)
    elif args.image:
        run_single(args.image, args.silent, args.mode)
    else:
        cam_index = ARM_CAMERA_INDEX if args.camera == "arm" else TABLE_CAMERA_INDEX
        if args.manual:
            run_manual(cam_index, args.silent, args.mode)
        else:
            run_autonomous(cam_index, args.silent, args.mode)


if __name__ == "__main__":
    main()
