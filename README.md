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

```
 +-----------+       +----------------+       +--------------+       +------------+
 |  SO-101   | ----> |  Table Camera  | ----> | Claude Vision| ----> | ElevenLabs |
 |  Arm      |       |  (wide shot)   |       |  (read page) |       |  (speak)   |
 | turn page |       |  captures      |       |  classify +  |       |  streaming  |
 |           |       |  full spread   |       |  extract text|       |  audio out  |
 +-----------+       +----------------+       +--------------+       +------------+
      ^                                                                     |
      |                   waits for speech to finish                        |
      +---------------------------------------------------------------------+
```

**One cycle:**

1. **Arm turns the page** and positions the camera overhead (one trained skill)
2. **Camera grabs a wide shot** of the full two-page spread
3. **Claude Vision classifies the page** -- is it blank, an index, a cover, a title page, table of contents, or content?
4. **Blank / index pages are auto-skipped** -- the arm turns again immediately
5. **Everything else gets read** -- Claude Vision extracts the text in visual reading order (top to bottom, left to right, left page first)
6. **ElevenLabs speaks it aloud** with streaming audio and a pre-fetch pipeline so there are no gaps between sentences
7. **Arm waits for speech to finish**, then turns the next page

## Key Features

**Intelligent page classification** -- A lightweight Claude Vision call (max 20 tokens) classifies each page before deciding what to do. The robot doesn't waste time trying to read a blank page or an index.

**Two reading modes** -- `skim` (default) reads only titles, headings, and section headers. `verbose` reads everything on the page, narrated naturally like someone reading to you.

**Spread-aware reading** -- The camera captures both pages at once. The prompt handles left-then-right reading order and recognizes when a title spans across both pages.

**Streaming audio pipeline** -- Three threads work in parallel: the main thread receives streamed text from Claude Vision, a pre-fetch thread sends completed sentences to ElevenLabs, and a playback thread plays audio chunks in order. The result: speech starts before the full page is even processed.

**Expressive voices** -- Randomly alternates between two ElevenLabs voices (Chantal and Kwame) for variety.

## Architecture

```
ladybugs-robotics/
  main.py                         # Main orchestrator (3 modes)
  src/
    config.py                     # API keys, camera indices, voices
    pipeline/
      camera.py                   # Persistent camera stream + one-shot capture
      page_reader.py              # Claude Vision reading + ElevenLabs speech
  test_data/                      # Sample book page images for testing
```

### `main.py` -- Three ways to run

| Mode | Command | Use case |
|------|---------|----------|
| **Interactive** | `python main.py` | Live with arm + camera. Press Enter after each page turn. |
| **Single image** | `python main.py --image test_data/page.jpg` | Test the reading pipeline on one page. |
| **Folder** | `python main.py --folder test_data/` | Batch-read a folder of page images in order. |

All modes support `--mode verbose`, `--mode skim`, and `--silent` (text only, no speech).

### `page_reader.py` -- The brain

- `classify_page()` -- Sends image to Claude Vision with a classification prompt. Returns one of: `blank`, `index`, `cover`, `title`, `toc`, `content`.
- `read_page_and_speak()` -- Streams text from Claude Vision and speaks sentences as they arrive using a pre-fetch audio pipeline.
- `read_page()` -- Silent mode. Sends image, returns extracted text.

### `camera.py` -- Persistent video stream

`CameraStream` keeps the camera feed open between page turns (no open/close overhead). Flushes stale frames from the buffer before each grab to ensure a fresh image.

## The Arm

We use the **SO-101** robotic arm (6-DOF, tabletop, gripper) with **Solo-CLI** for the full motor learning pipeline:

```bash
# Calibrate
solo calibrate --robot so101

# Teleoperate (human demonstrates, arm mirrors)
solo teleop --robot so101

# Record demonstrations
solo record --robot so101 --dataset ladybugs_read_book --episodes 10

# Train ACT policy (Action Chunking with Transformers)
solo train --dataset ladybugs_read_book --policy act

# Run autonomously
solo infer --robot so101 --policy act --checkpoint outputs/latest
```

**Current status:** Teleop demonstrations have been recorded. The arm learns a single combined skill -- turn the page and position the camera -- rather than separate skills for each action.

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
```

Test with a sample image:

```bash
python main.py --image test_data/page.jpg --mode verbose
```

Test with a folder of pages (simulates turning through a book):

```bash
python main.py --folder test_data/ --silent
```

Run live with camera:

```bash
python main.py --camera table --mode skim
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Robotic arm | SO-101 + Solo-CLI |
| Motor learning | ACT policy (Action Chunking with Transformers) |
| Page understanding | Claude Vision (Anthropic API) |
| Text-to-speech | ElevenLabs streaming API |
| Camera | OpenCV (persistent stream) |
| Language | Python |

## Team

**Ladybugs Robotics** -- Physical AI Hack 2026, San Francisco

Technical Team: Alison Cossette, Sudhir Dadi, Andreea Turcu

Support Team: Shola, Ted, Yolande

## License

MIT
