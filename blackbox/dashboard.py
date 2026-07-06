"""
Streamlit dashboard for viewing and verifying Black Box decision records.

Run from the project root:
    streamlit run blackbox/dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from blackbox.agent_demo import build_demo_decisions
    from blackbox.recorder import BlackBox, BlackBoxError
except ModuleNotFoundError:
    from agent_demo import build_demo_decisions
    from recorder import BlackBox, BlackBoxError


def load_css() -> None:
    """Load the dashboard stylesheet from the package directory."""
    css_path = Path(__file__).with_name("style.css")
    try:
        css = css_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        st.warning("style.css not found. Using default theme.")
        return

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _init_session_state() -> None:
    """Ensure session state holds a BlackBox instance with demo data loaded."""
    if "blackbox" not in st.session_state:
        st.session_state.blackbox = BlackBox()
        _load_demo_data()


def _load_demo_data() -> None:
    """Populate the recorder with sample agent decisions."""
    box: BlackBox = st.session_state.blackbox
    box.clear()
    for decision in build_demo_decisions():
        box.record(
            agent_name=str(decision["agent_name"]),
            prompt=str(decision["prompt"]),
            reasoning=str(decision["reasoning"]),
            tool_calls=list(decision["tool_calls"]),  # type: ignore[arg-type]
            output=str(decision["output"]),
        )


def _format_tool_calls(tool_calls: list[dict[str, Any]]) -> str:
    """Pretty-print tool call payloads for display."""
    return json.dumps(tool_calls, indent=2)


def _render_summary_metrics(box: BlackBox) -> None:
    """Show high-level stats at the top of the dashboard."""
    chain = box.chain
    total = len(chain)
    tampered = box.get_tampered_indices()
    verified_count = total - len(tampered)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Decisions", total)
    col2.metric("Verified Entries", verified_count)
    col3.metric("Tampered Entries", len(tampered))

    if total == 0:
        st.info("No recordings yet. Load demo data or run `python -m blackbox.agent_demo`.")
    elif box.verify():
        st.success("Chain verified — no tampering detected.")
    else:
        st.error(f"Chain tampered — {len(tampered)} entr{'y' if len(tampered) == 1 else 'ies'} affected.")


def _render_decisions_table(box: BlackBox) -> None:
    """Render a compact overview table of all decisions."""
    chain = box.chain
    if not chain:
        return

    rows = []
    for index, entry in enumerate(chain):
        is_valid = box.verify_entry(index)
        rows.append(
            {
                "#": index + 1,
                "Timestamp": entry["timestamp"],
                "Agent": entry["agent"],
                "Prompt": entry["prompt"][:80] + ("…" if len(entry["prompt"]) > 80 else ""),
                "Tools": len(entry["tool_calls"]),
                "Status": "Verified" if is_valid else "Tampered",
                "Hash": entry["hash"][:12] + "…",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_decision_cards(box: BlackBox) -> None:
    """Render expandable detail cards for each decision."""
    chain = box.chain
    if not chain:
        return

    st.subheader("Decision Details")

    for index, entry in enumerate(chain):
        is_valid = box.verify_entry(index)
        badge = "Verified" if is_valid else "Tampered"
        badge_color = "green" if is_valid else "red"

        label = f"Decision #{index + 1} — {entry['agent']} — {entry['timestamp'][:19]}"
        with st.expander(label, expanded=False):
            st.markdown(
                f"**Status:** :{badge_color}[{badge}] &nbsp;|&nbsp; "
                f"**Hash:** `{entry['hash'][:24]}…`"
            )

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("**Agent**")
                st.write(entry["agent"])
                st.markdown("**Prompt**")
                st.write(entry["prompt"])
                st.markdown("**Reasoning**")
                st.write(entry["reasoning"])

            with col_right:
                st.markdown("**Output**")
                st.write(entry["output"])
                st.markdown("**Tool Calls**")
                st.code(_format_tool_calls(entry["tool_calls"]), language="json")
                st.markdown("**Previous Hash**")
                st.code(entry["previous_hash"], language="text")


def main() -> None:
    """Entry point for the Streamlit dashboard."""
    st.set_page_config(
        page_title="Black Box — AI Flight Recorder",
        page_icon="🖤",
        layout="wide",
    )
    load_css()

    _init_session_state()
    box: BlackBox = st.session_state.blackbox

    st.title("Black Box")
    st.caption("Tamper-evident flight recorder for AI agent decisions")

    with st.sidebar:
        st.header("Controls")
        if st.button("Load demo data", use_container_width=True):
            try:
                _load_demo_data()
                st.success("Demo data loaded.")
            except BlackBoxError as exc:
                st.error(f"Failed to load demo data: {exc}")

        if st.button("Clear recordings", use_container_width=True):
            box.clear()
            st.warning("All recordings cleared.")

        st.divider()
        st.markdown(
            "**How it works**\n\n"
            "Each decision is hashed with SHA-256 and linked to the "
            "previous entry. Any modification breaks the chain."
        )

    _render_summary_metrics(box)

    st.divider()

    st.subheader("All Decisions")
    _render_decisions_table(box)

    st.divider()
    _render_decision_cards(box)


if __name__ == "__main__":
    main()
