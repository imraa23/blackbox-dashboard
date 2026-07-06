"""
Demo script — simulates three agent decisions and prints the hash chain.

Run from the project root:
    python -m blackbox.agent_demo
"""

from __future__ import annotations

import json
import sys

from blackbox.recorder import BlackBox, BlackBoxError


def build_demo_decisions() -> list[dict[str, object]]:
    """Return dummy agent decisions for demonstration purposes."""
    return [
        {
            "agent_name": "research-agent",
            "prompt": "Summarize the latest quarterly earnings report for ACME Corp.",
            "reasoning": (
                "The user wants a financial summary. I should fetch the report "
                "and extract revenue, profit, and guidance figures."
            ),
            "tool_calls": [
                {"tool": "web_search", "args": {"query": "ACME Corp Q1 2026 earnings"}},
                {"tool": "read_file", "args": {"path": "reports/acme-q1.pdf"}},
            ],
            "output": (
                "ACME Corp reported $2.1B revenue (+12% YoY), net income of $340M, "
                "and raised full-year guidance to $8.5–8.8B."
            ),
        },
        {
            "agent_name": "code-agent",
            "prompt": "Fix the failing unit test in tests/test_auth.py.",
            "reasoning": (
                "The test expects a 401 but gets 403. Likely the middleware order "
                "changed — I'll inspect auth.py and the test setup."
            ),
            "tool_calls": [
                {"tool": "read_file", "args": {"path": "tests/test_auth.py"}},
                {"tool": "read_file", "args": {"path": "src/auth.py"}},
                {"tool": "edit_file", "args": {"path": "src/auth.py", "change": "fix middleware order"}},
            ],
            "output": "Reordered JWT middleware before RBAC check. All 14 auth tests pass.",
        },
        {
            "agent_name": "deploy-agent",
            "prompt": "Deploy the staging build to production after CI passes.",
            "reasoning": (
                "CI is green on main@a3f9c2. I'll run the deployment playbook "
                "and monitor health checks for 60 seconds."
            ),
            "tool_calls": [
                {"tool": "run_command", "args": {"cmd": "ci status --branch main"}},
                {"tool": "run_command", "args": {"cmd": "deploy --env production --ref a3f9c2"}},
                {"tool": "health_check", "args": {"url": "https://api.example.com/health", "timeout": 60}},
            ],
            "output": "Deployment complete. All health checks passed. Production is live on a3f9c2.",
        },
    ]


def run_demo() -> int:
    """Create a BlackBox, record demo decisions, and print verification results."""
    box = BlackBox()

    print("=" * 60)
    print("Black Box — Agent Flight Recorder Demo")
    print("=" * 60)

    for index, decision in enumerate(build_demo_decisions(), start=1):
        try:
            entry = box.record(
                agent_name=str(decision["agent_name"]),
                prompt=str(decision["prompt"]),
                reasoning=str(decision["reasoning"]),
                tool_calls=list(decision["tool_calls"]),  # type: ignore[arg-type]
                output=str(decision["output"]),
            )
            print(f"\n[Recorded] Decision #{index}")
            print(f"  Agent:     {entry['agent']}")
            print(f"  Timestamp: {entry['timestamp']}")
            print(f"  Hash:      {entry['hash'][:16]}...")
        except BlackBoxError as exc:
            print(f"Failed to record decision #{index}: {exc}", file=sys.stderr)
            return 1

    print("\n" + "-" * 60)
    print("Full chain (JSON):")
    print("-" * 60)
    print(json.dumps(box.chain, indent=2))

    print("\n" + "-" * 60)
    print("Verification")
    print("-" * 60)
    is_valid = box.verify()
    status = "VERIFIED — chain intact" if is_valid else "TAMPERED — chain broken"
    print(f"  Chain status: {status}")
    print(f"  Total decisions: {len(box)}")

    for i in range(len(box)):
        entry_ok = box.verify_entry(i)
        badge = "Verified" if entry_ok else "Tampered"
        print(f"  Entry #{i + 1}: {badge}")

    return 0 if is_valid else 2


if __name__ == "__main__":
    raise SystemExit(run_demo())
