"""Perception skills -- camera + Claude Vision for scene understanding.

Three perception skills:
    - assess_scene : Look at the workspace and determine current state
    - read_left    : Read the left page of an open book spread
    - read_right   : Read the right page of an open book spread
"""

import anthropic

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from src.pipeline.camera import frame_to_base64
from src.pipeline.page_reader import read_page, read_page_and_speak


PROMPT_ASSESS_SCENE = (
    "Look at this image of a table or workspace. Determine the current state "
    "of the scene. Respond with ONLY one of the following labels, nothing else:\n\n"
    "  no_book       - no book is visible on the table\n"
    "  book_closed   - a book is present but closed\n"
    "  book_open     - a book is open and pages are visible\n"
    "  book_done     - the book is open to the last page or back cover\n"
)

PROMPT_READ_LEFT = (
    "You are reading a book aloud to a listener. This image shows an open book "
    "with two pages visible.\n\n"
    "Read ONLY the LEFT page. Ignore the right page entirely.\n"
    "Read top to bottom, left to right within the page.\n"
    "Never describe the page -- just read what's there.\n"
    "If a word is unclear, give your best guess.\n"
    "Read naturally, like storytime -- warm and human."
)

PROMPT_READ_RIGHT = (
    "You are reading a book aloud to a listener. This image shows an open book "
    "with two pages visible.\n\n"
    "Read ONLY the RIGHT page. Ignore the left page entirely.\n"
    "Read top to bottom, left to right within the page.\n"
    "Never describe the page -- just read what's there.\n"
    "If a word is unclear, give your best guess.\n"
    "Read naturally, like storytime -- warm and human."
)


def assess_scene(image_bytes: bytes) -> str:
    """Look at the scene and determine its current state.

    Returns one of: no_book, book_closed, book_open, book_done
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = frame_to_base64(image_bytes)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=20,
        system=PROMPT_ASSESS_SCENE,
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
                    {"type": "text", "text": "What is the current state of the scene?"},
                ],
            }
        ],
    )
    state = response.content[0].text.strip().lower()

    for known in ("no_book", "book_closed", "book_open", "book_done"):
        if known in state:
            return known
    return "book_open"  # default if response is ambiguous


def read_left(image_bytes: bytes, silent: bool = False, mode: str = "verbose") -> str:
    """Read the left page from a book spread image."""
    if silent:
        return read_page(image_bytes, mode=mode, system_prompt=PROMPT_READ_LEFT)
    return read_page_and_speak(image_bytes, silent=False, mode=mode,
                               system_prompt=PROMPT_READ_LEFT)


def read_right(image_bytes: bytes, silent: bool = False, mode: str = "verbose") -> str:
    """Read the right page from a book spread image."""
    if silent:
        return read_page(image_bytes, mode=mode, system_prompt=PROMPT_READ_RIGHT)
    return read_page_and_speak(image_bytes, silent=False, mode=mode,
                               system_prompt=PROMPT_READ_RIGHT)
