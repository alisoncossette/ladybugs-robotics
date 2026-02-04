# Setup Instructions

## Prerequisites

- Python 3.10+ (check with `python --version`)
- Git
- A Hugging Face account (https://huggingface.co/join)

## 1. Clone the Repo

```bash
git clone https://github.com/alisoncossette/ladybugs-robotics.git
cd ladybugs-robotics
```

## 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

- **Windows:** `source .venv/Scripts/activate`
- **Mac/Linux:** `source .venv/bin/activate`

You should see `(.venv)` in your terminal prompt.

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `solo-cli` and all its dependencies.

## 4. Log in to Hugging Face

Solo-CLI uses Hugging Face Hub for datasets and model checkpoints.

1. Create an access token at https://huggingface.co/settings/tokens
2. Run:

```bash
huggingface-cli login
```

3. Paste your token when prompted.

## 5. Verify Installation

```bash
solo --help
```

You should see the Solo-CLI help output with available commands.

---

## Role-Specific Setup

### Hardware (Sudhir)

Once at the SO-101 station:

```bash
# Calibrate the arm
solo calibrate --robot so101

# Test teleoperation (human moves leader arm, follower mirrors)
solo teleop --robot so101
```

### Models (Andreea)

```bash
# Record demonstrations (5-10 episodes)
solo record --robot so101 --dataset ladybugs_task1 --episodes 10

# Train ACT policy
solo train --dataset ladybugs_task1 --policy act

# Run inference
solo infer --robot so101 --policy act --checkpoint outputs/latest
```

### Context Graph (Shola, Ted, Yolande)

1. Install Neo4j Desktop from https://neo4j.com/download/
2. Create a new local database
3. Note the bolt URL (default: `bolt://localhost:7687`) and credentials
4. Additional Python dependencies for graph work:

```bash
pip install neo4j
```

---

## Troubleshooting

- **`solo` command not found:** Make sure your venv is activated.
- **HF authentication errors:** Re-run `huggingface-cli login` with a fresh token.
- **USB/serial issues with SO-101:** Check that the arm is powered on and connected. On Windows, check Device Manager for COM port assignment.
