# Ladybugs Robotics -- Project Plan

**Event origin:** Physical AI Hack 2026 (Jan 31 - Feb 1, San Francisco)
**Team:** Alison, Sudhir, Andreea, Shola, Ted, Yolande
**Hardware:** SO-101 robotic arm + LeRobot
**Award:** Best Overall / Most Impressive Project

---

## The Goal

A robotic arm that **autonomously reads a book**: assesses the scene, opens the book, turns pages, reads left then right, and closes when done -- all driven by a perception-action loop.

---

## Architecture: Six Skills

The system is built around six discrete skills -- three motor, three perception -- coordinated by an `assess_scene`-driven state machine.

### Motor Skills (Solo CLI + ACT policies)

Each motor skill is a separately trained ACT policy, executed via Solo CLI's inference mode. The `pexpect` wrapper automates the interactive CLI prompts so skills can be called programmatically from the orchestrator.

| Skill | What it does | Policy | Duration |
|-------|-------------|--------|----------|
| `open_book` | Open a closed book cover | `ladybugs/open_book_ACT` | ~15s |
| `close_book` | Close an open book | `ladybugs/close_book_ACT` | ~15s |
| `turn_page` | Turn one page right-to-left | `ladybugs/turn_page_ACT` | ~10s |

### Perception Skills (Camera + Claude Vision)

| Skill | What it does | Output |
|-------|-------------|--------|
| `assess_scene` | Look at the workspace, determine state | `no_book`, `book_closed`, `book_open`, `book_done` |
| `read_left` | Read the left page of an open spread | Streamed text + TTS audio |
| `read_right` | Read the right page of an open spread | Streamed text + TTS audio |

### Orchestrator State Machine

```
assess_scene
  → no_book      → done
  → book_closed  → open_book → assess_scene
  → book_open    → classify → read_left → read_right → turn_page → assess_scene
  → book_done    → close_book → done
```

---

## File Structure

```
ladybugs-robotics/
  main.py                             # Entry point (autonomous, manual, image, folder modes)
  requirements.txt                    # Dependencies
  src/
    config.py                         # API keys, camera indices, Solo CLI settings, skill policies
    pipeline/
      camera.py                       # Persistent camera stream + one-shot capture
      page_reader.py                  # Claude Vision reading + ElevenLabs streaming TTS
    skills/
      __init__.py                     # Skill exports
      motor.py                        # Motor skill wrapper (pexpect + Solo CLI)
      perception.py                   # assess_scene, read_left, read_right
      orchestrator.py                 # BookReaderOrchestrator state machine
  test_data/                          # Sample book page images for testing
```

---

## Phase Plan

### Phase 1: Hackathon (COMPLETE)
- [x] SO-101 calibrated and teleop working
- [x] Single combined skill trained (read_book)
- [x] Reading pipeline built (Claude Vision + ElevenLabs streaming TTS)
- [x] Page classification (blank, index, cover, title, toc, content)
- [x] End-to-end demo: turn → capture → classify → read → speak
- [x] Won Best Overall / Most Impressive Project

### Phase 2: Skill Architecture (COMPLETE)
- [x] Decompose monolithic skill into 6 discrete skills
- [x] Build motor skill wrapper with Solo CLI pexpect automation
- [x] Build perception skills (assess_scene, read_left, read_right)
- [x] Build orchestrator state machine
- [x] Add autonomous mode to main.py (default) + manual mode (--manual)

### Phase 3: Train Individual Motor Skills
- [ ] Record teleop demos for open_book (5-10 episodes)
- [ ] Record teleop demos for close_book (5-10 episodes)
- [ ] Record teleop demos for turn_page (5-10 episodes)
- [ ] Train separate ACT policies for each skill
- [ ] Test each skill in isolation via Solo CLI
- [ ] Update policy paths in config/.env

### Phase 4: Integration Testing
- [ ] Test full orchestrator loop with trained policies
- [ ] Tune skill durations based on actual execution times
- [ ] Test assess_scene accuracy across different book states
- [ ] Test read_left / read_right page isolation accuracy
- [ ] Handle edge cases (stuck pages, misaligned book, last page detection)

### Phase 5: Robustness
- [ ] Add error recovery (retry failed motor skills)
- [ ] Add "same page" detection (re-turn if page didn't flip)
- [ ] Add timeout/watchdog for stuck states
- [ ] Test with different books (size, binding, page thickness)

---

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
| Language | Python 3.10+ |
