"""Motor skills -- execute trained ACT policies via Solo CLI.

Each motor skill (open_book, close_book, turn_page) is a separately trained
ACT policy invoked through `solo robo --inference`. The pexpect wrapper
drives the interactive CLI prompts automatically.

Adapted from Physical-AI-hack-ServingU/serve_coffee.py pexpect pattern.
"""

import sys
from dataclasses import dataclass

try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False

from src.config import (
    SKILL_DURATIONS,
    SKILL_POLICIES,
    SOLO_CAMERA_0_ANGLE,
    SOLO_CAMERA_1_ANGLE,
    SOLO_FOLLOWER_ID,
    SOLO_SELECTED_CAMERAS,
)


@dataclass
class MotorSkill:
    """A trained motor skill backed by a Solo ACT policy."""

    name: str
    policy_path: str
    duration: int  # seconds
    task_description: str

    def execute(self) -> bool:
        """Run the skill via Solo CLI. Returns True on success."""
        print(f"[{self.name}] Executing (policy={self.policy_path}, {self.duration}s)...")

        if HAS_PEXPECT:
            return self._execute_pexpect()
        return self._execute_fallback()

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
            print(f"[{self.name}] Complete.")
            return True

        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            print(f"[{self.name}] Solo CLI error: {e}")
            try:
                child.close()
            except Exception:
                pass
            return False

    def _execute_fallback(self) -> bool:
        """Stub for environments without pexpect (Windows dev, testing).

        Logs what would happen and returns True so the orchestrator can
        continue its state machine during development.
        """
        print(f"[{self.name}] pexpect not available -- simulating skill execution")
        print(f"[{self.name}]   solo robo --inference")
        print(f"[{self.name}]   policy: {self.policy_path}")
        print(f"[{self.name}]   duration: {self.duration}s")
        print(f"[{self.name}]   task: {self.task_description}")
        print(f"[{self.name}] (simulated) Complete.")
        return True


# -- Defined motor skills -------------------------------------------------
# Policy paths are placeholders. Update in .env or config after training.

MOTOR_SKILLS = {
    "open_book": MotorSkill(
        name="open_book",
        policy_path=SKILL_POLICIES["open_book"],
        duration=SKILL_DURATIONS["open_book"],
        task_description="Open the book cover",
    ),
    "close_book": MotorSkill(
        name="close_book",
        policy_path=SKILL_POLICIES["close_book"],
        duration=SKILL_DURATIONS["close_book"],
        task_description="Close the book",
    ),
    "turn_page": MotorSkill(
        name="turn_page",
        policy_path=SKILL_POLICIES["turn_page"],
        duration=SKILL_DURATIONS["turn_page"],
        task_description="Turn one page from right to left",
    ),
}
