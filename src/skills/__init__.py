"""Ladybugs skill system.

Six skills for autonomous book reading:

Motor skills (trained ACT policies, executed via Solo CLI):
    - open_book   : Open a closed book
    - close_book  : Close an open book
    - turn_page   : Turn one page from right to left

Perception skills (camera + Claude Vision):
    - assess_scene : Determine the current state of the workspace
    - read_left    : Read the left page of an open book spread
    - read_right   : Read the right page of an open book spread
"""

from src.skills.motor import MOTOR_SKILLS
from src.skills.perception import assess_scene, read_left, read_right
from src.skills.orchestrator import BookReaderOrchestrator

__all__ = [
    "MOTOR_SKILLS",
    "assess_scene",
    "read_left",
    "read_right",
    "BookReaderOrchestrator",
]
