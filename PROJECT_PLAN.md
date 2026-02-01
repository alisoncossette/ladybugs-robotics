# Ladybugs Robotics -- Physical AI Hack 2026

**Event:** Physical AI Hack 2026 (Jan 31 - Feb 1, San Francisco)
**Team:** Alison, Sudhir, Andrea, Shola, Ted, Yolande
**Hardware:** SO-101 robotic arm + LeRobot

---

## The Goal

Teach a robotic arm to **read a book**: open it, turn pages, read the content aloud using a camera and a VLM.

---

## Step 1: Get the Robots Working

Everything else depends on this. We need:

1. SO-101 calibrated and responding
2. Teleoperation working (human moves leader arm, follower arm mirrors)
3. Dataset recorded (5-10 demos of a manipulation task)
4. ACT policy trained
5. Arm running autonomously (even if imperfectly)

### SO-101 Setup (Solo-CLI -- fastest path)

```bash
# Install Solo-CLI
pip install solo-cli

# Or clone from GitHub if pip isn't available
# git clone <solo-cli-repo>

# Calibrate the SO-101
solo calibrate --robot so101

# Test teleoperation
solo teleop --robot so101

# Record demonstrations (5-10 episodes)
solo record --robot so101 --dataset ladybugs_task1 --episodes 10

# Train ACT policy
solo train --dataset ladybugs_task1 --policy act

# Run inference (autonomous)
solo infer --robot so101 --policy act --checkpoint outputs/latest
```


### The Task: Read a Book

The arm learns to **open a book and turn pages**, then uses a camera to **read the content**.

Two sub-tasks:
1. **Physical manipulation** -- open the book, turn pages (trained via teleop demos)
2. **Vision/reading** -- camera captures the open page, VLM or OCR extracts the text

Environment quirks that matter:
- **Different books** -- varying sizes, binding stiffness, page thickness
- **Page sticking** -- some pages stick together
- **Book position** -- shifted or rotated on the table
- **Lighting** -- affects camera readability

---

## Step 2: Build the Reading Pipeline

While the arm is being trained, build the software that reads pages:
1. Camera captures a frame of the open page
2. Claude Vision extracts the text
3. Text-to-speech reads it aloud

This can be tested independently with saved images or a laptop camera.

---

## Phase Plan

### Phase 1: Get the arm working
- [ ] Claim SO-101 station
- [ ] Calibrate with Solo-CLI
- [ ] Test teleop
- [ ] Get Velda GPU access (one person, contact Solo Tech)

### Phase 2a: Practice run -- move a block
- [ ] Record 5-10 teleop demos of block pick-and-place
- [ ] Train ACT policy on Velda
- [ ] Test autonomous execution
- [ ] Confirm the full pipeline works: record → train → infer

### Phase 2b: Real task -- read a book
- [x] Task chosen: Read a Book (open, turn pages, read with camera)
- [ ] Record 5-10 teleop demos of opening book and turning pages
- [ ] Train ACT policy on Velda
- [ ] Set up camera pipeline for reading page content (VLM/OCR)
- [ ] Test autonomous execution

### Phase 3: Integrate arm + reading pipeline
- [ ] Arm opens book and turns page autonomously
- [ ] Camera captures the page
- [ ] VLM reads the text, speaks it aloud
- [ ] End-to-end demo: open → turn → read → speak

### Phase 4: Present
- [ ] Demo video (arm reading a book aloud)
- [ ] Presentation

---

## File Structure

```
ladybugs-robotics/
  PROJECT_PLAN.md           # This file
  SETUP.md                  # Setup instructions
  requirements.txt          # Dependencies
  src/
    config.py               # Configuration
    pipeline/
      camera.py             # Camera capture (arm + table)
      page_reader.py        # VLM reading + text-to-speech
  data/                     # Teleop demos (LeRobot format)
  models/                   # Trained checkpoints
```
