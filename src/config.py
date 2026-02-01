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
