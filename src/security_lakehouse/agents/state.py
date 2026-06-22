"""Agent run state and decision records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

AgentMode = Literal["rules_only", "model_assisted", "langgraph"]


@dataclass(frozen=True)
class AgentDecision:
    """A proposed or executed agent action."""

    action: str
    reason: str
    requires_approval: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
    status: Literal["proposed", "approved", "executed", "skipped"] = "proposed"


class AgentRunState(TypedDict, total=False):
    """State passed between deterministic or LangGraph agent nodes."""

    lake_dir: str
    role: str
    mode: AgentMode
    objective: str
    posture: dict[str, Any]
    evidence_gaps: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    decisions: list[AgentDecision]
    agent_budget: dict[str, Any]
    model_provider: dict[str, Any]
    model_context: dict[str, Any]
    model_output: dict[str, Any]
    evaluation: dict[str, Any]
    approved: bool
    errors: list[str]
