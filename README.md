# Ladybugs Robotics

**Physical AI Hack 2026 -- San Francisco, Jan 31 - Feb 1**

## What if a robot could read you a book?

We're teaching a robotic arm to **open a book, turn pages, and read the content aloud** using a camera and a vision-language model.

### How It Works

1. **Teleop training** -- A human demonstrates opening the book and turning pages using the leader arm. The follower arm mirrors the motion and we record the demonstrations.
2. **ACT policy** -- We train an ACT (Action Chunking with Transformers) policy on the recorded demos so the arm can do it autonomously.
3. **Vision reading** -- A camera captures the open page. Claude Vision extracts the text.
4. **Speech** -- The extracted text is read aloud using text-to-speech.

### Hardware

- **SO-101** robotic arm (tabletop, 6-DOF, gripper)
- **Solo-CLI** for calibration, teleop, recording, training, and inference
- **Two cameras** -- arm-mounted and table-view

## Setup

See [SETUP.md](SETUP.md) for full instructions.

```bash
git clone https://github.com/alisoncossette/ladybugs-robotics.git
cd ladybugs-robotics
python -m venv .venv
source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

## Project Structure

```
ladybugs-robotics/
  README.md
  PROJECT_PLAN.md
  SETUP.md
  requirements.txt
  src/
    config.py                    # Configuration
    pipeline/
      camera.py                  # Camera capture (arm + table)
      page_reader.py             # VLM reading + text-to-speech
  data/                          # Teleop demos (LeRobot format)
  models/                        # Trained policy checkpoints
```

## License

MIT
