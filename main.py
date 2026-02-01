"""Ladybugs Robotics -- Book Reader

Main orchestrator: captures a page from the camera and reads it aloud.

Usage:
    # Interactive mode: press Enter after each page turn
    python main.py

    # Use a specific camera
    python main.py --camera arm
    python main.py --camera table
    python main.py --camera both

    # Test with a saved image (no camera needed)
    python main.py --image test_data/page.jpg

    # Silent mode (text only, no speech)
    python main.py --silent
"""

import argparse
import sys

from src.config import ANTHROPIC_API_KEY, DEFAULT_CAMERA
from src.pipeline.page_reader import read_from_camera, read_from_file


def run_interactive(camera: str, silent: bool) -> None:
    """Interactive loop: press Enter to capture and read each page."""
    page_num = 0

    print("=" * 50)
    print("  LADYBUGS BOOK READER")
    print("=" * 50)
    print()
    print(f"Camera: {camera}")
    print(f"Speech: {'off' if silent else 'on'}")
    print()
    print("Press Enter to read a page. Type 'q' to quit.")
    print("-" * 50)

    while True:
        try:
            user_input = input("\n[Enter] Read page  |  [q] Quit > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nDone.")
            break

        if user_input == "q":
            print("Done.")
            break

        page_num += 1
        print(f"\n--- Page {page_num} ---")
        print("Capturing image...")

        try:
            result = read_from_camera(camera, silent=silent)
        except RuntimeError as e:
            print(f"Camera error: {e}")
            continue

        if silent and isinstance(result, dict):
            for cam_name, text in result.items():
                print(f"\n[{cam_name} camera]:")
                print(text)
        elif silent:
            print(f"\n{result}")

        print(f"\n--- End of page {page_num} ---")


def run_single(image_path: str, silent: bool) -> None:
    """Read a single image file."""
    print(f"Reading from image: {image_path}\n")
    text = read_from_file(image_path, silent=silent)
    if silent:
        print(text)


def main():
    parser = argparse.ArgumentParser(
        description="Ladybugs Book Reader: capture a page and read it aloud"
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
        help="Path to an image file (skips camera, reads once and exits)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Text output only, no speech",
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: Set ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY=your-key-here", file=sys.stderr)
        sys.exit(1)

    if args.image:
        run_single(args.image, args.silent)
    else:
        run_interactive(args.camera, args.silent)


if __name__ == "__main__":
    main()
