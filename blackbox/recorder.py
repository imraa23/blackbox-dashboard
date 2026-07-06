"""
Black Box recorder — tamper-evident, hash-chained flight recorder for AI agents.

Each decision is stored as a block linked to the previous block via SHA-256,
similar to a blockchain. Any modification to a past entry breaks the chain.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


# Sentinel value for the first block in the chain.
GENESIS_HASH = "GENESIS"


class BlackBoxError(Exception):
    """Raised when recorder operations fail validation or state checks."""


@dataclass
class DecisionEntry:
    """A single tamper-evident record of an agent decision."""

    timestamp: str
    agent: str
    prompt: str
    reasoning: str
    tool_calls: list[dict[str, Any]]
    output: str
    previous_hash: str
    entry_hash: str = field(default="", repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialize entry for display and persistence."""
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "prompt": self.prompt,
            "reasoning": self.reasoning,
            "tool_calls": self.tool_calls,
            "output": self.output,
            "previous_hash": self.previous_hash,
            "hash": self.entry_hash,
        }


class BlackBox:
    """
    In-memory flight recorder that chains agent decisions with SHA-256 hashes.

    Storage is kept in memory for the MVP; SQLite persistence can be added later.
    """

    def __init__(self) -> None:
        self._chain: list[DecisionEntry] = []

    @property
    def chain(self) -> list[dict[str, Any]]:
        """Return a read-only view of the chain as plain dictionaries."""
        return [entry.to_dict() for entry in self._chain]

    def __len__(self) -> int:
        return len(self._chain)

    def record(
        self,
        agent_name: str,
        prompt: str,
        reasoning: str,
        tool_calls: list[dict[str, Any]],
        output: str,
    ) -> dict[str, Any]:
        """
        Record a new agent decision and append it to the hash chain.

        Raises:
            BlackBoxError: If required fields are missing or invalid.
        """
        self._validate_record_input(agent_name, prompt, reasoning, tool_calls, output)

        previous_hash = self._chain[-1].entry_hash if self._chain else GENESIS_HASH
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build payload without the hash — the hash covers all other fields.
        payload = {
            "timestamp": timestamp,
            "agent": agent_name.strip(),
            "prompt": prompt,
            "reasoning": reasoning,
            "tool_calls": tool_calls,
            "output": output,
            "previous_hash": previous_hash,
        }
        entry_hash = self._compute_hash(payload)

        entry = DecisionEntry(
            timestamp=timestamp,
            agent=agent_name.strip(),
            prompt=prompt,
            reasoning=reasoning,
            tool_calls=tool_calls,
            output=output,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        self._chain.append(entry)
        return entry.to_dict()

    def verify(self) -> bool:
        """
        Verify the entire chain has not been tampered with.

        Checks both hash integrity and previous-hash linkage for every block.
        """
        if not self._chain:
            return True

        for index, entry in enumerate(self._chain):
            if not self._verify_entry_at_index(index):
                return False
        return True

    def verify_entry(self, index: int) -> bool:
        """
        Verify a single entry at the given index.

        Raises:
            BlackBoxError: If the index is out of range.
        """
        if index < 0 or index >= len(self._chain):
            raise BlackBoxError(f"Entry index out of range: {index}")
        return self._verify_entry_at_index(index)

    def get_tampered_indices(self) -> list[int]:
        """Return indices of all entries that fail verification."""
        return [i for i in range(len(self._chain)) if not self._verify_entry_at_index(i)]

    def _verify_entry_at_index(self, index: int) -> bool:
        entry = self._chain[index]

        # First block must reference the genesis sentinel.
        expected_previous = GENESIS_HASH if index == 0 else self._chain[index - 1].entry_hash
        if entry.previous_hash != expected_previous:
            return False

        payload = {
            "timestamp": entry.timestamp,
            "agent": entry.agent,
            "prompt": entry.prompt,
            "reasoning": entry.reasoning,
            "tool_calls": entry.tool_calls,
            "output": entry.output,
            "previous_hash": entry.previous_hash,
        }
        return self._compute_hash(payload) == entry.entry_hash

    @staticmethod
    def _compute_hash(payload: dict[str, Any]) -> str:
        """Compute a deterministic SHA-256 hash for a decision payload."""
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_record_input(
        agent_name: str,
        prompt: str,
        reasoning: str,
        tool_calls: list[dict[str, Any]],
        output: str,
    ) -> None:
        """Validate required fields before recording."""
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise BlackBoxError("agent_name must be a non-empty string")
        if not isinstance(prompt, str):
            raise BlackBoxError("prompt must be a string")
        if not isinstance(reasoning, str):
            raise BlackBoxError("reasoning must be a string")
        if not isinstance(tool_calls, list):
            raise BlackBoxError("tool_calls must be a list")
        if not isinstance(output, str):
            raise BlackBoxError("output must be a string")

    def load_chain(self, entries: list[dict[str, Any]]) -> None:
        """
        Replace the in-memory chain from serialized entries.

        Useful for testing or future persistence layers.
        """
        if not isinstance(entries, list):
            raise BlackBoxError("entries must be a list")

        loaded: list[DecisionEntry] = []
        for raw in entries:
            try:
                loaded.append(
                    DecisionEntry(
                        timestamp=raw["timestamp"],
                        agent=raw["agent"],
                        prompt=raw["prompt"],
                        reasoning=raw["reasoning"],
                        tool_calls=raw["tool_calls"],
                        output=raw["output"],
                        previous_hash=raw["previous_hash"],
                        entry_hash=raw["hash"],
                    )
                )
            except KeyError as exc:
                raise BlackBoxError(f"Invalid entry format: missing field {exc}") from exc

        self._chain = loaded

    def clear(self) -> None:
        """Remove all recorded decisions from memory."""
        self._chain.clear()
