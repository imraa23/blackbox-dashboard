# Black Box

**Black Box** is a tamper-evident, cryptographically-sealed flight recorder for AI agents. Every agent decision — prompt, reasoning, tool calls, and output — is recorded and linked into a hash chain. If anyone modifies a past entry, the chain breaks and verification fails.

## What it does

- **Records** each agent decision with timestamp, agent name, prompt, reasoning, tool calls, and output
- **Seals** every entry with SHA-256, chained to the previous entry (blockchain-style)
- **Verifies** the full chain or individual entries to detect tampering
- **Visualizes** recordings in a Streamlit dashboard with Verified / Tampered badges

## Install

From the `Black-Box` project root:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r blackbox/requirements.txt
```

## Run

### Demo (CLI)

Simulates three agent decisions, prints the hash chain, and reports verification status:

```bash
python -m blackbox.agent_demo
```

### Dashboard (Streamlit)

```bash
streamlit run run_dashboard.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`). Demo data loads automatically on first visit.

## Test

1. Run the demo and confirm output shows `VERIFIED — chain intact` and three `Verified` entries.
2. Launch the dashboard, load demo data, and confirm the table shows three decisions with green **Verified** badges.
3. Optional tamper test — in a Python shell:

```python
from blackbox.recorder import BlackBox
from blackbox.agent_demo import build_demo_decisions

box = BlackBox()
for d in build_demo_decisions():
    box.record(**{k: v for k, v in d.items() if k != "agent_name"}, agent_name=d["agent_name"])

assert box.verify() is True

# Simulate tampering
box._chain[0].output = "TAMPERED"
assert box.verify() is False
print("Tamper detection works.")
```

## Project layout

```
blackbox/
├── recorder.py      # BlackBox class — hash-chained recorder
├── dashboard.py     # Streamlit visualization
├── agent_demo.py    # CLI demo with dummy agent decisions
├── requirements.txt
└── README.md
```
