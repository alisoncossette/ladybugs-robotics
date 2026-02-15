# Ladybug Robotics

### What if a robot could read you a bedtime story?

**Physical AI Hack 2026 -- San Francisco, Jan 31 - Feb 1**
**Winner Best Overall/Most Impressive Project""

---

<div align="center">
  <video src="20260201_123707.mp4" width="100%" controls></video>
</div>

We built a robotic arm that **opens a book, turns pages, and reads the content aloud** -- combining learned motor skills with vision-language understanding and expressive text-to-speech.

The arm doesn't follow a script. It **sees** the page, **understands** what's on it, and **decides** how to read it -- skipping blank pages, reading titles on a cover, narrating chapter text like storytime.

<div align="center">
  <img src="open_book.gif" alt="Robot opening a book" width="270">
  &nbsp;&nbsp;&nbsp;
  <img src="page_turn_end.gif" alt="Robot turning a page" width="270">
</div>

## Listen: The Robot Reads a Book

https://github.com/user-attachments/assets/fd03ffa2-5871-4ac3-b7b6-337e29b443f9

## How It Works

Six skills work together in an `assess_scene`-driven loop:

```
                          ┌─────────────────────────────────────────┐
                          │          ASSESS SCENE                   │
                          │   (camera + Claude Vision)              │
                          └──────────┬──────────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
         book_closed            book_open              book_done
              │                      │                      │
              ▼                      ▼                      ▼
        ┌───────────┐    ┌───────────────────────┐   ┌───────────┐
        │ OPEN BOOK │    │ CLASSIFY              │   │ CLOSE BOOK│
        │  (motor)  │    │ READ LEFT  (perceive) │   │  (motor)  │
        └─────┬─────┘    │ READ RIGHT (perceive) │   └─────┬─────┘
              │          │ TURN PAGE  (motor)    │         │
              │          └───────────┬───────────┘         │
              │                      │                     │
              └──────────────────────┼─────────────────────┘
                                     │
                              assess_scene again
```

### The Six Skills

| Skill | Type | What it does |
|-------|------|-------------|
| `assess_scene` | Perception | Look at the workspace. Returns: `no_book`, `book_closed`, `book_open`, `book_done` |
| `open_book` | Motor | Open a closed book cover (trained ACT policy) |
| `close_book` | Motor | Close an open book (trained ACT policy) |
| `turn_page` | Motor | Turn one page from right to left (trained ACT policy) |
| `read_left` | Perception | Read the left page of a two-page spread aloud |
| `read_right` | Perception | Read the right page of a two-page spread aloud |

**Motor skills** are separately trained ACT policies executed via Solo CLI. The `pexpect` wrapper automates Solo's interactive prompts so each skill can be called programmatically.

**Perception skills** use the camera + Claude Vision. `assess_scene` is a lightweight classification call (~20 tokens). `read_left` and `read_right` use streaming text extraction with a pre-fetch TTS pipeline.

## Key Features

**Intelligent page classification** -- A lightweight Claude Vision call classifies each page before deciding what to do. The robot doesn't waste time trying to read a blank page or an index.

**Two reading modes** -- `skim` (default) reads only titles, headings, and section headers. `verbose` reads everything on the page, narrated naturally like someone reading to you.

**Left-then-right reading** -- Each page of the spread is read independently, left first then right, ensuring proper reading order.

**Streaming audio pipeline** -- Three threads work in parallel: the main thread receives streamed text from Claude Vision, a pre-fetch thread sends completed sentences to ElevenLabs, and a playback thread plays audio chunks in order. Speech starts before the full page is even processed.

**Expressive voices** -- Randomly alternates between two ElevenLabs voices (Chantal and Kwame) for variety.

**Autonomous operation** -- The `assess_scene` skill drives the entire loop. No human input needed once started.

## Architecture

```
ladybugs-robotics/
  main.py                         # Entry point (autonomous, manual, dry-run, image, folder)
  src/
    config.py                     # API keys, camera indices, Solo CLI settings, policies
    pipeline/
      camera.py                   # CameraStream, FolderImageSource, frame hashing
      page_reader.py              # Claude Vision reading + ElevenLabs speech
      archive.py                  # Save screenshots + text to timestamped sessions
    skills/
      __init__.py                 # Skill exports
      motor.py                    # Motor skill wrapper (pexpect + Solo CLI, retry logic)
      perception.py               # assess_scene, read_left, read_right
      orchestrator.py             # BookReaderOrchestrator state machine
  tests/
    test_orchestrator.py          # Unit tests (state machine, motor retry, camera, config)
    test_perception.py            # Integration tests (live Claude Vision API)
  test_data/                      # Sample book page images for testing
  archive/                        # Saved reading sessions (git-ignored)
```

### `main.py` -- Six ways to run

| Mode | Command | Use case |
|------|---------|----------|
| **Autonomous** | `python main.py` | Full skill loop with arm. Default mode. |
| **Dry-run** | `python main.py --dry-run --folder test_data/ --silent` | Walk the full state machine with test images, no hardware. |
| **Manual** | `python main.py --manual` | Press Enter to trigger each cycle. For debugging without arm. |
| **Single image** | `python main.py --image test_data/page.jpg` | Test the reading pipeline on one page. |
| **Folder** | `python main.py --folder test_data/` | Batch-read a folder of page images in order. |
| **Archive** | `python main.py --archive --silent --folder test_data/` | Save screenshots + text to `archive/`. |

All modes support `--mode verbose`, `--mode skim`, `--silent` (text only, no speech), `--archive`, and `--log-level`.

### `skills/` -- The skill system

- `motor.py` -- Wraps Solo CLI with `pexpect` to execute trained ACT policies programmatically. Falls back to simulation when pexpect is unavailable (Windows dev). Includes configurable retry logic with backoff.
- `perception.py` -- `assess_scene` classifies the workspace state. `read_left` and `read_right` read individual pages using Claude Vision + streaming TTS.
- `orchestrator.py` -- `BookReaderOrchestrator` runs the perception-action loop, using `assess_scene` to decide which skill to execute next. Includes same-page detection (frame hashing) to catch failed page turns.

### `pipeline/` -- Vision, speech, and archival

- `page_reader.py` -- Sends images to Claude Vision with reading prompts. Streams text and speaks sentences as they arrive using a pre-fetch audio pipeline.
- `camera.py` -- `CameraStream` keeps the camera feed open between page turns. `FolderImageSource` serves images from a directory for dry-run/testing. `frame_hash()` enables same-page detection.
- `archive.py` -- Saves camera frames and extracted text to timestamped session directories under `archive/`. Produces a `session.txt` with the full concatenated book text.

### `tests/` -- Test suite

- `test_orchestrator.py` -- 15 unit tests covering state machine transitions, motor skill retry logic, FolderImageSource, frame hashing, and startup validation. All mocked, no API calls needed.
- `test_perception.py` -- Integration tests that call the real Claude Vision API to validate assess_scene, classify_page, and read_left/read_right. Skipped automatically if `ANTHROPIC_API_KEY` is not set.

## Archive Mode

Add `--archive` to any mode to save every camera frame and extracted text to disk:

```bash
python main.py --archive --folder test_data/ --silent
```

Output structure:

```
archive/
  2026-02-07_143022/
    spread_001_frame.jpg          # Camera frame
    spread_001_left.txt           # Left page text
    spread_001_right.txt          # Right page text
    spread_001_meta.txt           # Page type + scene state
    spread_002_frame.jpg
    ...
    session.txt                   # Full concatenated text of the book
```

Useful for reviewing what the robot read, debugging perception accuracy, and building a record of reading sessions.

## Testing

```bash
# Run unit tests (no API key needed)
python -m unittest tests.test_orchestrator -v

# Run integration tests (requires ANTHROPIC_API_KEY)
python -m unittest tests.test_perception -v
```

Unit tests cover orchestrator state transitions, motor skill retry logic, FolderImageSource, frame hashing, and startup config validation. Integration tests call the live Claude Vision API to verify scene assessment, page classification, and left/right page reading.

## The Arm

We use the **SO-101** robotic arm (6-DOF, tabletop, gripper) with **Solo-CLI** for the full motor learning pipeline:

```bash
# Calibrate
solo calibrate --robot so101

# Teleoperate (human demonstrates, arm mirrors)
solo teleop --robot so101

# Record demonstrations for each skill separately
solo record --robot so101 --dataset ladybugs_open_book --episodes 10
solo record --robot so101 --dataset ladybugs_turn_page --episodes 10
solo record --robot so101 --dataset ladybugs_close_book --episodes 10

# Train ACT policies
solo train --dataset ladybugs_open_book --policy act
solo train --dataset ladybugs_turn_page --policy act
solo train --dataset ladybugs_close_book --policy act

# Run autonomously (called by the orchestrator via pexpect)
solo infer --robot so101 --policy act --checkpoint outputs/latest
```

## Quick Start

```bash
git clone https://github.com/alisoncossette/ladybugs-robotics.git
cd ladybugs-robotics
python -m venv .venv

# Windows
source .venv/Scripts/activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Set your API keys:

```bash
# .env file (not committed)
ANTHROPIC_API_KEY=your-key-here
ELEVENLABS_API_KEY=your-key-here

# Motor skill policies (update after training)
POLICY_OPEN_BOOK=ladybugs/open_book_ACT
POLICY_CLOSE_BOOK=ladybugs/close_book_ACT
POLICY_TURN_PAGE=ladybugs/turn_page_ACT
```

Test with a sample image:

```bash
python main.py --image test_data/page.jpg --mode verbose
```

Dry-run the full state machine with test images (no hardware):

```bash
python main.py --dry-run --folder test_data/ --silent
```

Test with a folder of pages (simulates turning through a book):

```bash
python main.py --folder test_data/ --silent
```

Archive a reading session (saves screenshots + text):

```bash
python main.py --archive --folder test_data/ --silent
```

Run live with camera (manual mode, no arm needed):

```bash
python main.py --manual --camera table --mode skim
```

Run autonomous (requires trained policies + arm):

```bash
python main.py
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Robotic arm | SO-101 + Solo-CLI |
| Motor learning | ACT policy (Action Chunking with Transformers) |
| Motor execution | Solo CLI via pexpect wrapper |
| Scene understanding | Claude Vision (Anthropic API) |
| Page reading | Claude Vision streaming |
| Text-to-speech | ElevenLabs streaming API |
| Camera | OpenCV (persistent stream) |
| Language | Python |

## Team

**Ladybugs Robotics** -- Physical AI Hack 2026, San Francisco

Technical Team: Alison Cossette, Sudhir Dadi, Andreea Turcu

Support Team: Shola, Ted, Yolande

## License

MIT
