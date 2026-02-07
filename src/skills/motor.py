"""Motor skills -- execute trained ACT policies via Solo CLI.

Each motor skill (open_book, close_book, turn_page) is a separately trained
ACT policy invoked through `solo robo --inference`. The pexpect wrapper
drives the interactive CLI prompts automatically.

Adapted from Physical-AI-hack-ServingU/serve_coffee.py pexpect pattern.
"""

import logging
import sys
import time
from dataclasses import dataclass

try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False

from src.config import (
    MOTOR_SKILL_MAX_RETRIES,
    SKILL_DURATIONS,
    SKILL_POLICIES,
    SOLO_CAMERA_0_ANGLE,
    SOLO_CAMERA_1_ANGLE,
    SOLO_FOLLOWER_ID,
    SOLO_SELECTED_CAMERAS,
)

log = logging.getLogger(__name__)


@dataclass
class MotorSkill:
    """A trained motor skill backed by a Solo ACT policy."""

    name: str
    policy_path: str
    duration: int  # seconds
    task_description: str
    dry_run: bool = False

    def execute(self, max_retries: int = MOTOR_SKILL_MAX_RETRIES) -> bool:
        """Run the skill via Solo CLI with retry logic. Returns True on success."""
        for attempt in range(1, max_retries + 1):
            log.info("[%s] Attempt %d/%d (policy=%s, %ds)",
                     self.name, attempt, max_retries, self.policy_path, self.duration)

            if self.dry_run or not HAS_PEXPECT:
                success = self._execute_fallback()
            else:
                success = self._execute_pexpect()

            if success:
                log.info("[%s] Complete.", self.name)
                return True

            if attempt < max_retries:
                wait = 2 * attempt
                log.warning("[%s] Failed. Retrying in %ds...", self.name, wait)
                time.sleep(wait)
            else:
                log.error("[%s] Failed after %d attempts.", self.name, max_retries)

        return False

    def _execute_pexpect(self) -> bool:
        """Drive Solo CLI interactively using pexpect."""
        child = pexpect.spawn(
            "solo robo --inference",
            encoding="utf-8",
            timeout=30,
        )
        child.logfile = sys.stdout

        try:
            child.expect("Would you like to use these preconfigured Inference settings")
            child.sendline("n")

            child.expect("Would you like to teleoperate during inference")
            child.sendline("n")

            child.expect("Enter follower id")
            child.sendline(str(SOLO_FOLLOWER_ID))

            child.expect("Enter policy path")
            child.sendline(self.policy_path)

            child.expect("Duration of inference session in seconds")
            child.sendline(str(self.duration))

            child.expect("Enter task description")
            child.sendline(self.task_description)

            child.expect("Enter viewing angle for Camera #0")
            child.sendline(SOLO_CAMERA_0_ANGLE)

            child.expect("Enter viewing angle for Camera #1")
            child.sendline(SOLO_CAMERA_1_ANGLE)

            child.expect("Select cameras")
            child.sendline(SOLO_SELECTED_CAMERAS)

            # Wait for the skill to finish
            child.expect(pexpect.EOF, timeout=self.duration + 10)
            child.close()
            return True

        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            log.error("[%s] Solo CLI error: %s", self.name, e)
            try:
                child.close()
            except Exception:
                pass
            return False

    def _execute_fallback(self) -> bool:
        """Stub for dry-run mode or environments without pexpect.

        Logs what would happen and returns True so the orchestrator can
        continue its state machine during development.
        """
        label = "dry-run" if self.dry_run else "simulated"
        log.info("[%s] (%s) solo robo --inference", self.name, label)
        log.info("[%s]   policy: %s", self.name, self.policy_path)
        log.info("[%s]   duration: %ds", self.name, self.duration)
        log.info("[%s]   task: %s", self.name, self.task_description)
        return True


def _build_motor_skills(dry_run: bool = False) -> dict[str, MotorSkill]:
    """Build the motor skill registry."""
    return {
        "open_book": MotorSkill(
            name="open_book",
            policy_path=SKILL_POLICIES["open_book"],
            duration=SKILL_DURATIONS["open_book"],
            task_description="Open the book cover",
            dry_run=dry_run,
        ),
        "close_book": MotorSkill(
            name="close_book",
            policy_path=SKILL_POLICIES["close_book"],
            duration=SKILL_DURATIONS["close_book"],
            task_description="Close the book",
            dry_run=dry_run,
        ),
        "turn_page": MotorSkill(
            name="turn_page",
            policy_path=SKILL_POLICIES["turn_page"],
            duration=SKILL_DURATIONS["turn_page"],
            task_description="Turn one page from right to left",
            dry_run=dry_run,
        ),
    }


# Default motor skills (live mode)
MOTOR_SKILLS = _build_motor_skills(dry_run=False)
