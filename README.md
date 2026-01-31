# Ladybugs Robotics

**Physical AI Hack 2026 -- San Francisco, Jan 31 - Feb 1**

## What if robots could remember?

A robot trained on 10 demonstrations knows how to pick up a puzzle piece. But it doesn't know that *this* puzzle piece is warped, or *that* block is heavier than it looks, or the surface it's working on is slippery today.

When it fails, a human corrects it. The question is: **what happens to that correction?**

### The Experiment

We run an A/B test comparing two approaches to robot adaptation:

| | **A: Knowledge Graph** | **B: Fine-Tuning** |
|---|---|---|
| Robot fails on a quirky object | Same failure | Same failure |
| Human provides correction | Same correction | Same correction |
| What happens next | Correction stored in a knowledge graph. Next attempt retrieves relevant context and injects it as a language instruction. **No weight update.** | Correction demonstrated via teleop. Policy retrained on N+1 demos. **Weights updated.** |
| Second encounter with same object | Graph lookup. Immediate. | Baked into weights. No lookup. |

We measure:
- **Attempts to succeed** after receiving a correction
- **Time to adapt** from failure to success
- **Generalization** -- does knowledge about one quirky object transfer to similar objects?

### Why a Graph, Not a Prompt?

The knowledge graph is not a list of corrections appended to a prompt. It is structured, queryable, and supports reasoning:

1. **Selective retrieval**: The robot picks up Object B. The graph returns only Object B's known quirks -- not every correction ever made. As the environment grows, the query stays focused.

2. **Similarity-based transfer**: Object C is new, but the graph knows `C --similar_to--> A` (both are warped). The robot applies A's learned quirks to C without ever failing on C. This is graph traversal, not prompt engineering.

3. **Typed relationships**: Observations are stored as structured nodes and edges -- `(Object)-[:HAS_QUIRK]->(Quirk)-[:AFFECTS]->(Task)` -- not as raw text. This enables queries like "which objects have friction issues?" or "what quirks affect insertion tasks?"

4. **Contradiction handling**: If correction 1 says "push harder" and correction 3 says "don't push so hard," each is attached to a specific object-task-attempt context. The graph resolves which applies to the current situation.

5. **Persistence and scale**: The graph survives across sessions, environments, and robots. 100 objects with 5 quirks each is 500 observations. A prompt chokes. A graph returns the 2-3 that matter.

### Two Graphs

**Attempt Graph** -- what happened:
- Each attempt: task, object, actions, outcome (success/failure)
- Human feedback given, and by whom
- What changed between attempts
- The trajectory of learning over time

**Environment Graph** -- what the robot knows about its world:
- Objects and their quirks
- Locations and their properties
- Which quirks affect which tasks
- Similarity relationships between objects (for generalization)

### Hardware

- **SO-101** robotic arm (tabletop, 6-DOF, gripper)
- **LeRobot** framework (HuggingFace) for data collection, training, and inference
- **ACT** (Action Chunking with Transformers) as the base policy
- **Neo4j** for the knowledge graph

### Team

- **Alison** -- System architect, intelligence layer, graph integration, presentation
- **Andrea** -- Policy pipeline, SO-101 setup, data collection, ACT training, fine-tuning path
- **Yolande** -- Neo4j, graph schema design, Cypher queries, graph visualization
- **Sudhir** -- Perception, speech-to-text, dashboard, data collection

## Setup

```bash
# Clone
git clone https://github.com/ladybugs-robotics/ladybugs-robotics.git
cd ladybugs-robotics

# Install dependencies
pip install -r requirements.txt

# SO-101 quickstart (Solo-CLI)
solo calibrate --robot so101
solo teleop --robot so101
solo record --robot so101 --dataset ladybugs_task1 --episodes 10
solo train --dataset ladybugs_task1 --policy act
solo infer --robot so101 --policy act --checkpoint outputs/latest
```

## Project Structure

```
ladybugs-robotics/
  README.md
  PROJECT_PLAN.md
  requirements.txt
  src/
    graph/
      schema.py            # Neo4j graph schema (nodes, relationships)
      environment_graph.py # Object quirks, similarity, task relationships
      attempt_graph.py     # Attempt logging, outcome tracking
      queries.py           # Cypher query builders
    pipeline/
      correction_separator.py  # Skill vs environment classification
      context_builder.py       # Graph query -> language instruction
      demo_loop.py             # Main experiment loop
    config.py
  data/                    # Teleop demonstrations (LeRobot format)
  models/                  # Trained policy checkpoints
  results/                 # A/B test measurements
```

## License

MIT
