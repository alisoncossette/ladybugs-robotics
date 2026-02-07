"""Configuration for the Ladybugs Robotics pipeline."""

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# -- Logging ---------------------------------------------------------------

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configure structured logging for the entire application."""
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


# -- Startup validation ----------------------------------------------------

def validate_config(silent: bool = False, dry_run: bool = False) -> None:
    """Check that all required environment variables are set.

    Raises SystemExit with a clear message if anything is missing.
    """
    errors = []

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is not set")

    if not silent and not ELEVENLABS_API_KEY:
        errors.append("ELEVENLABS_API_KEY is not set (required unless --silent)")

    if errors:
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        print("\nSet these in your .env file or environment.", file=sys.stderr)
        sys.exit(1)

# Camera device indices (update based on your hardware setup)
ARM_CAMERA_INDEX = int(os.environ.get("ARM_CAMERA_INDEX", 0))
TABLE_CAMERA_INDEX = int(os.environ.get("TABLE_CAMERA_INDEX", 1))

# Anthropic API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# ElevenLabs API
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICES = {
    "chantal": "XyeTSqCjJXIeZoB4YnOs",
    "kwame": "ohGUGM5CpTBCkBU3BE42",
}

# Reading settings
DEFAULT_CAMERA = os.environ.get("DEFAULT_CAMERA", "table")  # "arm", "table", or "both"

# Solo CLI settings (for motor skill execution)
SOLO_FOLLOWER_ID = int(os.environ.get("SOLO_FOLLOWER_ID", 1))
SOLO_CAMERA_0_ANGLE = os.environ.get("SOLO_CAMERA_0_ANGLE", "wrist")
SOLO_CAMERA_1_ANGLE = os.environ.get("SOLO_CAMERA_1_ANGLE", "top")
SOLO_SELECTED_CAMERAS = os.environ.get("SOLO_SELECTED_CAMERAS", "0,1")

# Motor skill policy paths (update after training each skill)
SKILL_POLICIES = {
    "open_book": os.environ.get("POLICY_OPEN_BOOK", "ladybugs/open_book_ACT"),
    "close_book": os.environ.get("POLICY_CLOSE_BOOK", "ladybugs/close_book_ACT"),
    "turn_page": os.environ.get("POLICY_TURN_PAGE", "ladybugs/turn_page_ACT"),
}

# Motor skill durations in seconds
SKILL_DURATIONS = {
    "open_book": int(os.environ.get("DURATION_OPEN_BOOK", 15)),
    "close_book": int(os.environ.get("DURATION_CLOSE_BOOK", 15)),
    "turn_page": int(os.environ.get("DURATION_TURN_PAGE", 10)),
}

# Motor skill retry settings
MOTOR_SKILL_MAX_RETRIES = int(os.environ.get("MOTOR_SKILL_MAX_RETRIES", 2))
