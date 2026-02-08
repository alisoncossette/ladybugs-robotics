# Ladybug Robotics -- Internal Dev

Private repo for active development. Public hackathon showcase: [ladybugs-robotics](https://github.com/alisoncossette/ladybugs-robotics)

---

## Setup

```bash
git clone https://github.com/alisoncossette/ladybug-robotics-private.git
cd ladybug-robotics-private
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file (not committed):

```
ANTHROPIC_API_KEY=your-key-here
ELEVENLABS_API_KEY=your-key-here

# Motor skill policies (update after training)
POLICY_OPEN_BOOK=ladybugs/open_book_ACT
POLICY_CLOSE_BOOK=ladybugs/close_book_ACT
POLICY_TURN_PAGE=ladybugs/turn_page_ACT
```

## Running

| Mode | Command | Use case |
|------|---------|----------|
| **Autonomous** | `python main.py` | Full skill loop with arm |
| **Dry-run** | `python main.py --dry-run --folder test_data/ --silent` | Full state machine, no hardware |
| **Manual** | `python main.py --manual` | Press Enter each cycle, no arm needed |
| **Single image** | `python main.py --image test_data/page.jpg` | Test reading on one page |
| **Folder** | `python main.py --folder test_data/` | Batch-read pages in order |

**Flags:** `--mode verbose|skim`, `--silent`, `--archive`, `--log-level DEBUG|INFO|WARNING|ERROR`

## Testing

```bash
# Unit tests (no API key needed, ~10s)
python -m unittest tests.test_orchestrator -v

# Integration tests (requires ANTHROPIC_API_KEY)
python -m unittest tests.test_perception -v
```

## Architecture

```
src/
  config.py                     # API keys, camera indices, Solo CLI settings, policies
  pipeline/
    camera.py                   # CameraStream, FolderImageSource, frame hashing
    page_reader.py              # Claude Vision reading + ElevenLabs streaming TTS
    archive.py                  # Save frames + text to archive/<timestamp>/
  skills/
    motor.py                    # Motor skill wrapper (pexpect + Solo CLI, retry logic)
    perception.py               # assess_scene, read_left, read_right
    orchestrator.py             # BookReaderOrchestrator state machine
tests/
  test_orchestrator.py          # 15 unit tests (mocked, no API)
  test_perception.py            # Integration tests (live Claude Vision)
```

## State Machine

```
assess_scene
  -> no_book      -> done
  -> book_closed  -> open_book -> assess_scene
  -> book_open    -> classify -> read_left -> read_right -> turn_page -> assess_scene
  -> book_done    -> close_book -> done
```

## The Six Skills

| Skill | Type | Implementation |
|-------|------|---------------|
| `assess_scene` | Perception | Claude Vision classification (~20 tokens) |
| `read_left` | Perception | Claude Vision + streaming TTS (left page only) |
| `read_right` | Perception | Claude Vision + streaming TTS (right page only) |
| `open_book` | Motor | ACT policy via Solo CLI / pexpect |
| `close_book` | Motor | ACT policy via Solo CLI / pexpect |
| `turn_page` | Motor | ACT policy via Solo CLI / pexpect |

Motor skills fall back to simulation stubs on Windows (no pexpect).

## Training Motor Skills

When the SO-101 arrives:

```bash
# 1. Calibrate
solo calibrate --robot so101

# 2. Record demonstrations (5-10 episodes each)
solo record --robot so101 --dataset ladybugs_open_book --episodes 10
solo record --robot so101 --dataset ladybugs_turn_page --episodes 10
solo record --robot so101 --dataset ladybugs_close_book --episodes 10

# 3. Train ACT policies
solo train --dataset ladybugs_open_book --policy act
solo train --dataset ladybugs_turn_page --policy act
solo train --dataset ladybugs_close_book --policy act

# 4. Update .env with policy paths
# 5. Test: python main.py --manual
# 6. Full run: python main.py
```

## Archive Mode

`--archive` saves frames and text to `archive/<timestamp>/`:

```
archive/2026-02-07_143022/
  spread_001_frame.jpg
  spread_001_left.txt
  spread_001_right.txt
  spread_001_meta.txt
  session.txt               # Full concatenated book text
```

## Roadmap

Tracked via [GitHub Issues](https://github.com/alisoncossette/ladybug-robotics-private/issues).

**Done:** Skill architecture, orchestrator, hardening (retry, same-page detection, logging, validation), tests, archive mode.

**Next:** Train individual motor skills (open_book, close_book, turn_page), integration testing with hardware, robustness tuning.

## Team

Alison Cossette, Sudhir Dadi (modestapproach), Andreea Turcu (Andreea292)
