"""Optional LangGraph workflows around TrustOps facts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from security_lakehouse.agents.providers import ModelProviderConfig, provider_from_env
from security_lakehouse.agents.state import AgentDecision, AgentRunState
from security_lakehouse.agents.tools import load_evidence_gaps, load_redacted_posture, propose_evidence_gap_actions


def _load_posture_node(state: AgentRunState) -> AgentRunState:
    return {
        **state,
        "posture": load_redacted_posture(state["lake_dir"], role=state.get("role", "read_only")),
    }


def _load_gaps_node(state: AgentRunState) -> AgentRunState:
    return {
        **state,
        "evidence_gaps": load_evidence_gaps(state["lake_dir"], role=state.get("role", "read_only")),
    }


def _propose_actions_node(state: AgentRunState) -> AgentRunState:
    decisions = [
        AgentDecision(
            action=str(item["action"]),
            reason=str(item["reason"]),
            requires_approval=bool(item["requires_approval"]),
            payload={"control_id": item["control_id"]},
            status="proposed",
        )
        for item in propose_evidence_gap_actions(state.get("evidence_gaps", []))
    ]
    return {**state, "decisions": decisions}


def run_posture_review(
    lake_dir: str | Path,
    *,
    role: str = "read_only",
    objective: str = "Review posture and propose evidence-gap actions.",
    provider: ModelProviderConfig | None = None,
) -> AgentRunState:
    """Run the posture-review harness without requiring LangGraph or an LLM."""
    provider = provider or provider_from_env()
    state: AgentRunState = {
        "lake_dir": str(lake_dir),
        "role": role,
        "objective": objective,
        "mode": "rules_only",
        "errors": [],
    }
    # The first shipped path is deliberately deterministic. Model-backed nodes
    # can enrich summaries later, but they must consume this redacted state.
    if provider.enabled:
        state["errors"] = [f"model provider {provider.provider!r} configured; model-backed nodes not enabled yet"]
    state = _load_posture_node(state)
    state = _load_gaps_node(state)
    state = _propose_actions_node(state)
    return state


def build_posture_review_graph() -> Any:
    """Build a LangGraph StateGraph when the optional extra is installed."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:  # pragma: no cover - exercised without optional extra
        raise RuntimeError("install trustops-security-data-lake[agents] to use LangGraph orchestration") from exc

    graph = StateGraph(AgentRunState)
    graph.add_node("load_posture", _load_posture_node)
    graph.add_node("load_evidence_gaps", _load_gaps_node)
    graph.add_node("propose_actions", _propose_actions_node)
    graph.set_entry_point("load_posture")
    graph.add_edge("load_posture", "load_evidence_gaps")
    graph.add_edge("load_evidence_gaps", "propose_actions")
    graph.add_edge("propose_actions", END)
    return graph.compile()
