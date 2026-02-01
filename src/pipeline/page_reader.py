"""Read the content of a book page using Claude Vision, then speak it aloud.

Usage:
    # Read from table camera and speak aloud
    python -m src.pipeline.page_reader

    # Read from arm camera
    python -m src.pipeline.page_reader --camera arm

    # Read from both cameras (picks the best result)
    python -m src.pipeline.page_reader --camera both

    # Read from a saved image file
    python -m src.pipeline.page_reader --image path/to/page.jpg

    # Silent mode (no speech, just print text)
    python -m src.pipeline.page_reader --silent
"""

import argparse
import sys

import anthropic
import pyttsx3

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, DEFAULT_CAMERA
from src.pipeline.camera import (
    capture_arm_camera,
    capture_both,
    capture_table_camera,
    frame_to_base64,
)

SYSTEM_PROMPT = (
    "You are a reading assistant for a robotic arm. "
    "You receive an image of an open book page captured by a camera. "
    "Your job is to extract and return the text on the visible page(s). "
    "Return ONLY the text content, preserving paragraph breaks. "
    "If the image is blurry, angled, or partially obscured, do your best "
    "and note any parts you are unsure about in [brackets]."
)


def read_page(image_bytes: bytes) -> str:
    """Send a page image to Claude Vision and return the extracted text."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = frame_to_base64(image_bytes)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Read this book page and return the text.",
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def read_from_file(image_path: str) -> str:
    """Read a page from a saved image file."""
    with open(image_path, "rb") as f:
        return read_page(f.read())


def speak(text: str) -> None:
    """Read text aloud using text-to-speech."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def read_from_camera(camera: str = DEFAULT_CAMERA) -> str | dict[str, str]:
    """Capture and read from the specified camera(s).

    Args:
        camera: "arm", "table", or "both"

    Returns:
        Extracted text (str), or dict of {camera_name: text} if "both".
    """
    if camera == "arm":
        return read_page(capture_arm_camera())
    elif camera == "table":
        return read_page(capture_table_camera())
    elif camera == "both":
        frames = capture_both()
        return {name: read_page(data) for name, data in frames.items()}
    else:
        raise ValueError(f"Unknown camera: {camera}. Use 'arm', 'table', or 'both'.")


def main():
    parser = argparse.ArgumentParser(description="Read a book page via camera + VLM")
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
        help="Path to a saved image file (skips camera capture)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Don't read aloud, just print the text",
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: Set ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    if args.image:
        print(f"Reading from image: {args.image}\n")
        text = read_from_file(args.image)
        print(text)
        if not args.silent:
            speak(text)
    else:
        print(f"Capturing from camera: {args.camera}\n")
        result = read_from_camera(args.camera)
        if isinstance(result, dict):
            for cam_name, text in result.items():
                print(f"--- {cam_name} camera ---")
                print(text)
                print()
                if not args.silent:
                    speak(text)
        else:
            print(result)
            if not args.silent:
                speak(result)


if __name__ == "__main__":
    main()
