# Ladybugs Robotics -- Physical AI Hack 2026

**Event:** Physical AI Hack 2026 (Jan 31 - Feb 1, San Francisco)
**Team:** Alison, Sudhir, Andrea, Shola, Ted, Yolande
**Hardware:** SO-101 robotic arm + LeRobot

---

## The Experiment

**Hypothesis:** When a robot encounters environment-specific quirks that its base policy wasn't trained on, retrieving context from a knowledge graph is more efficient and/or effective than fine-tuning the policy on additional demonstrations.

### A/B Test

| | **A: Context Graph** | **B: Fine-Tuning** |
|---|---|---|
| Base policy | ACT trained on N demos | ACT trained on N demos (same) |
| Robot fails because of environment quirk | Same failure | Same failure |
| Human provides correction | Same correction | Same correction |
| What happens next | Correction stored in graph. Next attempt gets language context injected into policy. No weight update. | Correction demo added to training set. Policy retrained on N+1 demos. Weights updated. |
| Second encounter | Graph lookup. Immediate adaptation. | Baked into weights. No lookup needed. |
| Measure: attempts to succeed | ? | ? |
| Measure: time to adapt | ? | ? |
| Measure: generalization to similar objects | ? | ? |

### Two Graphs

**Attempt Graph** -- tracks what happened across attempts:
- Each attempt: what task, what object, what the robot did, success/failure
- What feedback was given, by whom
- What changed between attempts
- The trajectory of learning

**Environment Graph** -- persistent knowledge of the world:
- Objects and their quirks
- Locations and their properties
- Which quirks affect which tasks
- Similarity between objects (for generalization)

---

## Step 1: Get the Robots Working

Everything else depends on this. No intelligence layer, no graphs, no VLM until we have:

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

## Step 2: Record Failures

Once the policy runs autonomously on the book task, introduce environment quirks:
- Swap to a different book (different size, binding, page thickness)
- Rotate or shift the book on the table
- Use pages that stick together
- Change lighting conditions (affects reading accuracy)

Record these failures. These are the test cases for the A/B comparison.

---

## Step 3: Build Both Paths

### Path A: Context Graph
- Human provides verbal feedback about the quirk
- Separator classifies: skill vs environment
- Environment observation stored in graph
- Next attempt: query graph, inject context
- If using SmolVLA: context goes into language instruction
- If using ACT: context displayed to human operator for validation (ACT has no language input)

### Path B: Fine-Tuning
- Human demonstrates the correct approach (teleop)
- New demo added to dataset
- Policy retrained (or fine-tuned from checkpoint)
- Next attempt: run updated policy

### Measure Both
- Attempts to succeed on the quirky object
- Wall-clock time from failure to success
- Does knowledge transfer to similar objects?
- Does the correction persist across sessions?

---

## Team Roles

### Alison -- Architect
- System design, integration
- Overall architecture and decision-making
- Presentation

### Sudhir -- Hardware Owner
- SO-101 setup, calibration, teleop
- Camera/perception setup
- Hardware debugging and maintenance

### Andrea -- Models
- ACT training (and SmolVLA if time)
- Fine-tuning pipeline (graph B path)
- Policy inference and debugging
- Data collection

### Shola, Ted, Yolande -- Context Graph
- Neo4j setup
- Graph schema (attempt graph + environment graph)
- Cypher queries
- Context retrieval and injection (graph A path)
- Graph visualization for presentation

---

## Phase Plan

### Phase 1: Get the arm working
- [ ] Claim SO-101 station
- [ ] Calibrate with Solo-CLI
- [ ] Test teleop
- [ ] Get Velda GPU access (one person, contact Solo Tech)

### Phase 2: Collect data + train
- [x] Task chosen: Read a Book (open, turn pages, read with camera)
- [ ] Record 5-10 teleop demos of opening book and turning pages
- [ ] Train ACT policy on Velda
- [ ] Set up camera pipeline for reading page content (VLM/OCR)
- [ ] Test autonomous execution

### Phase 3: Create failures + build paths
- [ ] Introduce environment quirks (different books, lighting, positioning)
- [ ] Record failures
- [ ] Build context graph path (Shola, Ted, Yolande)
- [ ] Build fine-tuning path (Andrea)
- [ ] Set up Neo4j (Shola, Ted, Yolande)

### Phase 4: Run A/B test
- [ ] Same failure, both paths, measure results
- [ ] Try multiple objects/quirks
- [ ] Record everything

### Phase 5: Present
- [ ] Graph visualization (Shola, Ted, Yolande)
- [ ] Results comparison table
- [ ] Demo video (arm reading a book)
- [ ] Presentation

---

## File Structure

```
ladybugs-robotics/
  PROJECT_PLAN.md           # This file
  requirements.txt          # Dependencies
  src/
    environment_memory.py   # Context graph path: separator + store + recall
    attempt_tracker.py      # Attempt graph: logs every attempt and outcome
    vlm_compare.py          # VLM failure vs success comparison
    demo_loop.py            # Main loop: attempt -> fail -> correct -> retry
    config.py               # Configuration
  data/                     # Teleop demos (LeRobot format)
  models/                   # Trained checkpoints
  results/                  # A/B test measurements
```
