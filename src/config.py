"""Configuration for the Ladybugs Robotics pipeline."""

import os
from dotenv import load_dotenv

load_dotenv()

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
