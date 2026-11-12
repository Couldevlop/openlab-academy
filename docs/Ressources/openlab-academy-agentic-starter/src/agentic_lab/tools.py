from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentic_lab.workflow import LocalWorkflow

ToolFunction = Callable[[dict[str, Any]], dict[str, Any]]


def build_registry(workflow: LocalWorkflow) -> dict[str, ToolFunction]:
    """Liste blanche explicite : seuls ces cinq outils peuvent être invoqués."""
    return {
        "lister_factures_impayees": workflow.list_invoices,
        "calculer_exposition": workflow.calculate_exposure,
        "preparer_brouillon_relance": workflow.prepare_draft,
        "soumettre_pour_validation": workflow.submit_for_approval,
        "enregistrer_relance_simulee": workflow.record_simulated_reminder,
    }


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    workflow: LocalWorkflow | None = None,
) -> dict[str, Any]:
    """Point de contrôle unique ; un outil absent de la liste blanche est journalisé."""
    service = workflow or LocalWorkflow()
    registry = build_registry(service)
    tool = registry.get(name)
    if tool is None:
        return service.blocked_tool(name)
    if not isinstance(arguments, dict):
        return {"ok": False, "erreur": "Les arguments doivent être un objet JSON."}
    try:
        return tool(arguments)
    except Exception as exc:  # noqa: BLE001 - frontière de sécurité : toute erreur d'outil devient un résultat contrôlé
        return {"ok": False, "erreur": f"Erreur contrôlée dans l'outil : {type(exc).__name__}"}
