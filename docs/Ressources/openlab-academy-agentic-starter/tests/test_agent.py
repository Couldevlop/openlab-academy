from agentic_lab.agent import run_agent
from agentic_lab.tools import execute_tool
from agentic_lab.workflow import LocalWorkflow


def test_demo_returns_expected_summary(tmp_path):
    workflow = LocalWorkflow(state_path=tmp_path / "state.json")
    result = run_agent(max_steps=5, workflow=workflow)
    assert result.status == "completed"
    assert "5 facture(s)" in result.final_text
    assert "7 730 000 F CFA" in result.final_text  # espaces insecables
    assert all(item["tool"] != "envoyer_email" for item in result.observations)


def test_unknown_tool_is_rejected_and_logged(tmp_path):
    workflow = LocalWorkflow(state_path=tmp_path / "state.json")
    result = execute_tool("envoyer_email", {"to": "person@example.test"}, workflow)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert workflow.snapshot()["blocked_tools"][-1]["name"] == "envoyer_email"


def test_invalid_search_argument_is_rejected(tmp_path):
    workflow = LocalWorkflow(state_path=tmp_path / "state.json")
    result = execute_tool("lister_factures_impayees", {"age_min_jours": -1}, workflow)
    assert result["ok"] is False
    assert result["erreur"] == "Arguments invalides"


def test_extra_argument_is_rejected(tmp_path):
    workflow = LocalWorkflow(state_path=tmp_path / "state.json")
    result = execute_tool("lister_factures_impayees", {"age_min_jours": 30, "admin": True}, workflow)
    assert result["ok"] is False


def test_step_limit_stops_agent(tmp_path):
    workflow = LocalWorkflow(state_path=tmp_path / "state.json")
    result = run_agent(max_steps=1, workflow=workflow)
    assert result.status == "max_steps_reached"
    assert result.steps == 1
    assert "validation humaine" in result.final_text
