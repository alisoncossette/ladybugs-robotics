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
import os
import random
import re
import subprocess
import sys
import tempfile
import threading

import anthropic
from elevenlabs import ElevenLabs

from src.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    DEFAULT_CAMERA,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_VOICE_NAME,
)
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


def _play_audio(filepath: str) -> None:
    """Play an mp3 file using the system's default player."""
    if sys.platform == "win32":
        os.startfile(filepath)
    elif sys.platform == "darwin":
        subprocess.run(["afplay", filepath], capture_output=True)
    else:
        subprocess.run(["mpv", "--no-video", filepath], capture_output=True)


def _speak_chunk(client: ElevenLabs, voice_id: str, text: str, chunk_num: int) -> None:
    """Generate and play audio for a single chunk of text."""
    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
    )
    audio_bytes = b"".join(audio_generator)
    tmp = os.path.join(tempfile.gettempdir(), f"ladybugs_speech_{chunk_num}.mp3")
    with open(tmp, "wb") as f:
        f.write(audio_bytes)
    _play_audio(tmp)
    # Wait for playback to roughly finish
    import time
    word_count = len(text.split())
    time.sleep(max(1.5, word_count / 2.5))


def read_page_and_speak(image_bytes: bytes, silent: bool = False) -> str:
    """Stream text from Claude Vision and speak sentences as they arrive."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = frame_to_base64(image_bytes)

    if not silent:
        print(f"[Speaking as: {ELEVENLABS_VOICE_NAME}]")
        eleven = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # Stream from Claude Vision
    full_text = ""
    buffer = ""
    chunk_num = 0
    sentence_end = re.compile(r'[.!?]\s')

    with client.messages.stream(
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
    ) as stream:
        for text_chunk in stream.text_stream:
            full_text += text_chunk
            print(text_chunk, end="", flush=True)

            if not silent:
                buffer += text_chunk
                # Speak when we have a complete sentence
                match = sentence_end.search(buffer)
                if match:
                    end_pos = match.end()
                    sentence = buffer[:end_pos].strip()
                    buffer = buffer[end_pos:]
                    if sentence:
                        chunk_num += 1
                        _speak_chunk(eleven, ELEVENLABS_VOICE_ID, sentence, chunk_num)

    # Speak any remaining text in the buffer
    if not silent and buffer.strip():
        chunk_num += 1
        _speak_chunk(eleven, ELEVENLABS_VOICE_ID, buffer.strip(), chunk_num)

    print()  # newline after streaming
    return full_text


def read_page(image_bytes: bytes) -> str:
    """Send a page image to Claude Vision and return the extracted text (no speech)."""
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


def read_from_file(image_path: str, silent: bool = False) -> str:
    """Read a page from a saved image file."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    if silent:
        return read_page(image_bytes)
    return read_page_and_speak(image_bytes, silent=False)


def speak(text: str) -> None:
    """Read text aloud using ElevenLabs text-to-speech."""
    print(f"[Speaking as: {ELEVENLABS_VOICE_NAME}]")
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=ELEVENLABS_VOICE_ID,
        model_id="eleven_multilingual_v2",
    )

    audio_bytes = b"".join(audio_generator)
    tmp = os.path.join(tempfile.gettempdir(), "ladybugs_speech.mp3")
    with open(tmp, "wb") as f:
        f.write(audio_bytes)
    _play_audio(tmp)
    import time
    word_count = len(text.split())
    time.sleep(max(3, word_count / 2.5))


def read_from_camera(camera: str = DEFAULT_CAMERA, silent: bool = False) -> str | dict[str, str]:
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
                results[cam_name] = read_page(data)
            else:
                results[cam_name] = read_page_and_speak(data)
        return results
    else:
        raise ValueError(f"Unknown camera: {camera}. Use 'arm', 'table', or 'both'.")

    if silent:
        return read_page(img)
    return read_page_and_speak(img)


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
        text = read_from_file(args.image, silent=args.silent)
        if args.silent:
            print(text)
    else:
        print(f"Capturing from camera: {args.camera}\n")
        result = read_from_camera(args.camera, silent=args.silent)
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
