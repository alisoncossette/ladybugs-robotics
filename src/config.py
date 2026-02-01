"""Configuration for the Ladybugs Robotics pipeline."""

import os

# Camera device indices (update based on your hardware setup)
ARM_CAMERA_INDEX = int(os.environ.get("ARM_CAMERA_INDEX", 0))
TABLE_CAMERA_INDEX = int(os.environ.get("TABLE_CAMERA_INDEX", 1))

# Anthropic API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Reading settings
DEFAULT_CAMERA = os.environ.get("DEFAULT_CAMERA", "table")  # "arm", "table", or "both"
