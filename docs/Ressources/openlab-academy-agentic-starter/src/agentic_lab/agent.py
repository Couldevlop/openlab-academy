from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic_lab.tools import execute_tool
from agentic_lab.workflow import LocalWorkflow


@dataclass
class AgentRun:
    status: str
    steps: int
    observations: list[dict[str, Any]]
    final_text: str


DEFAULT_PLAN: list[tuple[str, dict[str, Any]]] = [
    ("lister_factures_impayees", {"age_min_jours": 30, "exclure_litiges": True}),
    ("calculer_exposition", {"facture_ids": "$factures_trouvees"}),
]


def run_agent(
    plan: list[tuple[str, dict[str, Any]]] | None = None,
    max_steps: int = 5,
    workflow: LocalWorkflow | None = None,
) -> AgentRun:
    """Boucle déterministe de formation : les décisions sont simulées, pas un LLM."""
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or not 1 <= max_steps <= 20:
        raise ValueError("max_steps doit être un entier compris entre 1 et 20.")
    service = workflow or LocalWorkflow()
    actions = plan if plan is not None else DEFAULT_PLAN
    observations: list[dict[str, Any]] = []
    facts: list[str] = []

    for index, (tool_name, raw_args) in enumerate(actions[:max_steps], start=1):
        arguments = dict(raw_args)
        if arguments.get("facture_ids") == "$factures_trouvees":
            arguments["facture_ids"] = facts
        result = execute_tool(tool_name, arguments, service)
        observations.append({"step": index, "tool": tool_name, "arguments": arguments, "result": result})
        if not result.get("ok"):
            return AgentRun("error", index, observations, result.get("erreur", "Erreur contrôlée."))
        if tool_name == "lister_factures_impayees":
            facts = [row["facture_id"] for row in result["factures"]]

    if len(actions) > max_steps:
        return AgentRun(
            "max_steps_reached",
            max_steps,
            observations,
            f"Plafond de {max_steps} étape(s) atteint ; arrêt contrôlé et validation humaine requise.",
        )

    if len(observations) >= 2 and observations[1]["tool"] == "calculer_exposition":
        total = observations[1]["result"].get("total_eur", 0.0)
        return AgentRun(
            "completed",
            len(observations),
            observations,
            f"Analyse terminée : {len(facts)} facture(s) éligible(s), exposition de {total:.2f} EUR. Aucune relance envoyée.",
        )
    return AgentRun("completed", len(observations), observations, "Plan exécuté sans envoi externe.")


def run_demo(max_steps: int = 5, verbose: bool = True) -> str:
    result = run_agent(max_steps=max_steps)
    if verbose:
        for observation in result.observations:
            print(f"[étape {observation['step']}] outil={observation['tool']} -> {observation['result']}")
    return result.final_text
