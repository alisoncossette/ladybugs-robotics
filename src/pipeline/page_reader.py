"""Read the content of a book page using Claude Vision, then speak it aloud.

Usage:
    # Read from table camera and speak aloud
    python -m src.pipeline.page_reader

    # Read from arm camera
    python -m src.pipeline.page_reader --camera arm

    # Read from both cameras
    python -m src.pipeline.page_reader --camera both

    # Read from a saved image file
    python -m src.pipeline.page_reader --image path/to/page.jpg

    # Silent mode (no speech, just print text)
    python -m src.pipeline.page_reader --silent
"""

import argparse
import os
import queue
import random
import re
import subprocess
import sys
import tempfile
import threading
import time

import anthropic
from elevenlabs import ElevenLabs

from src.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    DEFAULT_CAMERA,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICES,
)
from src.pipeline.camera import (
    capture_arm_camera,
    capture_both,
    capture_table_camera,
    frame_to_base64,
)

_BASE_RULES = (
    "You are reading a book aloud to a listener. You receive an image of an open book "
    "showing one or two pages (a spread).\n\n"
    "CRITICAL RULES:\n"
    "1. First, determine the page orientation. The image may be rotated or angled. "
    "Mentally rotate it so the text is upright before reading.\n"
    "2. If two pages are visible, read the LEFT page first, then the RIGHT page.\n"
    "3. Within each page, read top to bottom, left to right.\n"
    "4. If a title or header spans both pages, read it once.\n"
    "5. Do NOT rearrange text by size or importance -- follow the physical layout.\n"
    "6. For structural pages (cover, title page, table of contents): "
    "read all the text as it appears.\n\n"
    "Never describe the page. Never say 'This page contains...' or 'The header reads...'. "
    "Just read what's there. If a word is unclear, give your best guess."
)

PROMPT_VERBOSE = (
    _BASE_RULES + "\n\n"
    "Read EVERYTHING on the page: titles, headings, subheadings, and all body text.\n"
    "For content pages, read naturally, like storytime -- warm and human. "
    "Flow smoothly from sentence to sentence."
)

PROMPT_SKIM = (
    _BASE_RULES + "\n\n"
    "ONLY read titles, headings, section headers, subheadings, and chapter names. "
    "Skip all body/paragraph text. Read them in the order they appear on the page."
)

PROMPT_CLASSIFY = (
    "Look at this image of a book page. Classify it as ONE of the following types. "
    "Respond with ONLY the type label, nothing else.\n\n"
    "  blank     - empty page, no meaningful text\n"
    "  index     - index, glossary, or bibliography page\n"
    "  cover     - front or back cover\n"
    "  title     - title page, half-title, or dedication page\n"
    "  toc       - table of contents\n"
    "  content   - regular content page (chapter text, articles, etc.)\n"
)

# Page types that should be read aloud
READ_TYPES = {"cover", "title", "toc", "content"}
# Page types that should be skipped
SKIP_TYPES = {"blank", "index"}


def _pick_voice() -> tuple[str, str]:
    """Randomly pick a voice. Returns (name, voice_id)."""
    name = random.choice(list(ELEVENLABS_VOICES.keys()))
    return name, ELEVENLABS_VOICES[name]


def classify_page(image_bytes: bytes) -> str:
    """Classify a page image. Returns one of: blank, index, cover, title, toc, content."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = frame_to_base64(image_bytes)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=20,
        system=PROMPT_CLASSIFY,
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
                    {"type": "text", "text": "Classify this page."},
                ],
            }
        ],
    )
    page_type = response.content[0].text.strip().lower()
    # Normalize to known types
    for known in ("blank", "index", "cover", "title", "toc", "content"):
        if known in page_type:
            return known
    return "content"  # default to content if unclear


def _fetch_audio(client: ElevenLabs, voice_id: str, text: str) -> bytes:
    """Fetch audio bytes from ElevenLabs for a chunk of text."""
    audio_stream = client.text_to_speech.stream(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
    )
    return b"".join(audio_stream)


def _play_audio_bytes(audio_bytes: bytes, text: str, chunk_num: int) -> None:
    """Play audio bytes using the system player."""
    tmp = os.path.join(tempfile.gettempdir(), f"ladybugs_speech_{chunk_num}.mp3")
    with open(tmp, "wb") as f:
        f.write(audio_bytes)

    if sys.platform == "win32":
        os.startfile(tmp)
        word_count = len(text.split())
        time.sleep(max(1.5, word_count / 2.5))
    elif sys.platform == "darwin":
        subprocess.run(["afplay", tmp], capture_output=True)
    else:
        subprocess.run(["mpv", "--no-video", "--no-terminal", tmp],
                        capture_output=True)


def _audio_worker(audio_queue: queue.Queue) -> None:
    """Background worker: plays audio chunks from the queue in order."""
    chunk_num = 0
    while True:
        item = audio_queue.get()
        if item is None:  # poison pill
            break
        audio_bytes, text = item
        chunk_num += 1
        _play_audio_bytes(audio_bytes, text, chunk_num)
        audio_queue.task_done()


def read_page_and_speak(image_bytes: bytes, silent: bool = False, mode: str = "skim",
                        system_prompt: str | None = None) -> str:
    """Stream text from Claude Vision and speak sentences as they arrive.

    Uses a pre-fetch pipeline: while one sentence plays, the next is already
    being synthesized by ElevenLabs, reducing gaps between sentences.
    """
    prompt = system_prompt or (PROMPT_VERBOSE if mode == "verbose" else PROMPT_SKIM)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = frame_to_base64(image_bytes)

    if not silent:
        voice_name, voice_id = _pick_voice()
        print(f"[Speaking as: {voice_name}] [mode: {mode}]")
        eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio_q = queue.Queue()
        player_thread = threading.Thread(target=_audio_worker, args=(audio_q,), daemon=True)
        player_thread.start()

    full_text = ""
    buffer = ""
    sentence_end = re.compile(r'[.!?]\s')
    prefetch_thread = None

    def _prefetch_and_queue(el_client, vid, sentence_text):
        """Fetch audio and put it on the playback queue."""
        audio = _fetch_audio(el_client, vid, sentence_text)
        audio_q.put((audio, sentence_text))

    with client.messages.stream(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=prompt,
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
    ) as stream:
        for text_chunk in stream.text_stream:
            full_text += text_chunk
            print(text_chunk, end="", flush=True)

            if not silent:
                buffer += text_chunk
                match = sentence_end.search(buffer)
                if match:
                    end_pos = match.end()
                    sentence = buffer[:end_pos].strip()
                    buffer = buffer[end_pos:]
                    if sentence:
                        # Wait for any previous prefetch to finish
                        if prefetch_thread and prefetch_thread.is_alive():
                            prefetch_thread.join()
                        # Start fetching audio in background
                        prefetch_thread = threading.Thread(
                            target=_prefetch_and_queue,
                            args=(eleven, voice_id, sentence),
                        )
                        prefetch_thread.start()

    # Handle remaining buffer
    if not silent and buffer.strip():
        if prefetch_thread and prefetch_thread.is_alive():
            prefetch_thread.join()
        prefetch_thread = threading.Thread(
            target=_prefetch_and_queue,
            args=(eleven, voice_id, buffer.strip()),
        )
        prefetch_thread.start()

    if not silent:
        # Wait for all audio to be fetched
        if prefetch_thread and prefetch_thread.is_alive():
            prefetch_thread.join()
        # Signal player thread to stop after draining
        audio_q.put(None)
        player_thread.join()

    print()  # newline after streaming
    return full_text


def read_page(image_bytes: bytes, mode: str = "skim",
              system_prompt: str | None = None) -> str:
    """Send a page image to Claude Vision and return the extracted text (no speech)."""
    prompt = system_prompt or (PROMPT_VERBOSE if mode == "verbose" else PROMPT_SKIM)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = frame_to_base64(image_bytes)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=prompt,
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


def read_from_file(image_path: str, silent: bool = False, mode: str = "skim") -> str:
    """Read a page from a saved image file."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    if silent:
        return read_page(image_bytes, mode=mode)
    return read_page_and_speak(image_bytes, silent=False, mode=mode)


def speak(text: str) -> None:
    """Read text aloud using ElevenLabs text-to-speech."""
    voice_name, voice_id = _pick_voice()
    print(f"[Speaking as: {voice_name}]")
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    audio_bytes = _fetch_audio(client, voice_id, text)
    _play_audio_bytes(audio_bytes, text, 0)


def read_from_camera(camera: str = DEFAULT_CAMERA, silent: bool = False, mode: str = "skim") -> str | dict[str, str]:
    """Capture and read from the specified camera(s)."""
    if camera == "arm":
        img = capture_arm_camera()
    elif camera == "table":
        img = capture_table_camera()
    elif camera == "both":
        frames = capture_both()
        results = {}
        for cam_name, data in frames.items():
            print(f"\n[{cam_name} camera]:")
            if silent:
                results[cam_name] = read_page(data, mode=mode)
            else:
                results[cam_name] = read_page_and_speak(data, mode=mode)
        return results
    else:
        raise ValueError(f"Unknown camera: {camera}. Use 'arm', 'table', or 'both'.")

    if silent:
        return read_page(img, mode=mode)
    return read_page_and_speak(img, mode=mode)


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
    parser.add_argument(
        "--mode",
        choices=["verbose", "skim"],
        default="skim",
        help="verbose = read everything, skim = titles/headings only (default: skim)",
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("Error: Set ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    if args.image:
        print(f"Reading from image: {args.image}\n")
        text = read_from_file(args.image, silent=args.silent, mode=args.mode)
        if args.silent:
            print(text)
    else:
        print(f"Capturing from camera: {args.camera}\n")
        result = read_from_camera(args.camera, silent=args.silent, mode=args.mode)
        if args.silent:
            if isinstance(result, dict):
                for cam_name, text in result.items():
                    print(f"--- {cam_name} camera ---")
                    print(text)
                    print()
            else:
                print(result)


if __name__ == "__main__":
    main()
