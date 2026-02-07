"""Ladybugs Robotics -- Book Reader

SO-101 robotic arm opens a book, reads pages aloud, and turns pages.

Six skills work together in an assess_scene-driven loop:
    Motor skills  : open_book, close_book, turn_page (Solo CLI + ACT policies)
    Perception    : assess_scene, read_left, read_right (camera + Claude Vision)

Autonomous flow:
    1. assess_scene → determine workspace state
    2. Execute skill(s) based on state (open, read, turn, close)
    3. Repeat until done

Usage:
    # Autonomous mode -- full skill loop with arm
    python main.py

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
import os
import sys

from src.config import ANTHROPIC_API_KEY, ARM_CAMERA_INDEX, DEFAULT_CAMERA, TABLE_CAMERA_INDEX
from src.pipeline.page_reader import (
    READ_TYPES,
    SKIP_TYPES,
    classify_page,
    read_from_camera,
    read_from_file,
    read_page,
    read_page_and_speak,
)


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
        print(f"No images found in {folder_path}")
        return

    print("=" * 50)
    print("  LADYBUGS BOOK READER")
    print("=" * 50)
    print()
    print(f"Pages found: {len(files)}")
    print(f"Mode:   {mode}")
    print(f"Speech: {'off' if silent else 'on'}")
    print("-" * 50)

    for i, filepath in enumerate(files, 1):
        filename = os.path.basename(filepath)
        print(f"\n--- Page {i}/{len(files)}: {filename} ---")

        page_type, text = _read_image_bytes(filepath, silent, mode)

        if page_type in SKIP_TYPES:
            print(f"[{page_type} page -- skipping]")
            continue

        print(f"[{page_type}]")
        if silent:
            print(text)

        print(f"--- End of page {i} ---")

    print("\n" + "=" * 50)
    print("  DONE")
    print("=" * 50)


def run_single(image_path: str, silent: bool, mode: str) -> None:
    """Read a single image file with classification."""
    print(f"Reading from image: {image_path}\n")

    page_type, text = _read_image_bytes(image_path, silent, mode)

    if page_type in SKIP_TYPES:
        print(f"[{page_type} page -- would skip in auto mode]")
        return

    print(f"[{page_type}]")
    if silent:
        print(text)


def _process_frame(img: bytes, page_num: int, side: str,
                    silent: bool, mode: str) -> str:
    """Classify and read a single frame. Returns the page type."""
    page_type = classify_page(img)
    label = f"Page {page_num} ({side})" if side else f"Page {page_num}"
    print(f"[{label}: {page_type}]")

    if page_type in SKIP_TYPES:
        print(f"  Skipping {page_type} page...")
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

    print("=" * 50)
    print("  LADYBUGS BOOK READER -- MANUAL MODE")
    print("=" * 50)
    print()
    print(f"Camera index: {camera_index}")
    print(f"Speech: {'off' if silent else 'on'}")
    print(f"Mode:   {mode}")
    print()
    print("Press Enter after each page turn. Type 'q' to quit.")
    print("-" * 50)

    with CameraStream(camera_index) as stream:
        print("Camera stream open.")

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
            print(f"\n--- Spread {page_num} ---")

            # Grab wide shot of both pages
            img = stream.grab()
            _process_frame(img, page_num, "", silent, mode)

            print(f"\n--- End of spread {page_num} ---")


def run_autonomous(camera_index: int, silent: bool, mode: str) -> None:
    """Autonomous mode -- full skill loop driven by assess_scene.

    The orchestrator runs a perception-action loop:
        assess_scene → open_book / read_left+read_right+turn_page / close_book
    """
    from src.pipeline.camera import CameraStream
    from src.skills.orchestrator import BookReaderOrchestrator

    with CameraStream(camera_index) as stream:
        orchestrator = BookReaderOrchestrator(stream, silent=silent, mode=mode)
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
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: Set ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY=your-key-here", file=sys.stderr)
        sys.exit(1)

    if args.folder:
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
