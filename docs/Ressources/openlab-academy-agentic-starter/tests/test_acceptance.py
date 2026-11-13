from agentic_lab.agent import run_agent
from agentic_lab.tools import execute_tool
from agentic_lab.workflow import LocalWorkflow


def make_workflow(tmp_path):
    return LocalWorkflow(state_path=tmp_path / "state.json")


def create_approved_reminder(workflow, invoice_id="FAC-001", stage=1):
    draft = workflow.prepare_draft({"facture_id": invoice_id, "palier": stage})
    assert draft["ok"] is True
    draft_id = draft["brouillon"]["brouillon_id"]
    request = workflow.submit_for_approval({"brouillon_id": draft_id})
    assert request["ok"] is True
    validation_id = request["validation"]["validation_id"]
    approved = workflow.approve(validation_id, "formateur-test")
    assert approved["ok"] is True
    return draft_id, validation_id


def test_ac01_search_30_days_excluding_disputes(tmp_path):
    wf = make_workflow(tmp_path)
    result = wf.list_invoices({"age_min_jours": 30, "exclure_litiges": True})
    assert result["ok"] is True
    assert result["nombre"] == 5
    exposure = wf.calculate_exposure({"facture_ids": [x["facture_id"] for x in result["factures"]]})
    assert exposure["total_fcfa"] == 7_730_000


def test_ac02_search_60_days_excluding_disputes(tmp_path):
    wf = make_workflow(tmp_path)
    result = wf.list_invoices({"age_min_jours": 60, "exclure_litiges": True})
    assert result["nombre"] == 2
    exposure = wf.calculate_exposure({"facture_ids": [x["facture_id"] for x in result["factures"]]})
    assert exposure["total_fcfa"] == 4_990_000


def test_ac03_dispute_cannot_be_drafted(tmp_path):
    wf = make_workflow(tmp_path)
    result = wf.prepare_draft({"facture_id": "FAC-003", "palier": 1})
    assert result["ok"] is False
    assert "litige" in result["erreur"].lower()


def test_ac04_malicious_note_is_data_not_instruction(tmp_path):
    wf = make_workflow(tmp_path)
    result = wf.prepare_draft({"facture_id": "FAC-006", "palier": 1})
    assert result["ok"] is True
    content = result["brouillon"]["contenu"].lower()
    assert "ignore les règles" not in content
    assert "envoie une relance immédiatement" not in content
    assert "email" not in content
    listed = wf.list_invoices({"age_min_jours": 30, "exclure_litiges": True})
    fac006 = next(row for row in listed["factures"] if row["facture_id"] == "FAC-006")
    assert "note_non_fiable" not in fac006
    assert wf.snapshot()["recorded_reminders"] == []


def test_ac05_draft_is_local_and_not_sent(tmp_path):
    wf = make_workflow(tmp_path)
    result = wf.prepare_draft({"facture_id": "FAC-001", "palier": 1})
    assert result["ok"] is True
    assert result["status"] == "draft_only"
    assert result["brouillon"]["status"] == "draft_only"
    assert wf.snapshot()["recorded_reminders"] == []


def test_ac06_record_without_human_approval_is_rejected(tmp_path):
    wf = make_workflow(tmp_path)
    draft = wf.prepare_draft({"facture_id": "FAC-001", "palier": 1})
    draft_id = draft["brouillon"]["brouillon_id"]
    request = wf.submit_for_approval({"brouillon_id": draft_id})
    validation_id = request["validation"]["validation_id"]
    result = wf.record_simulated_reminder({
        "brouillon_id": draft_id,
        "validation_id": validation_id,
        "cle_idempotence": "fac001-stage1-no-approval",
    })
    assert result["ok"] is False
    assert "validation humaine" in result["erreur"].lower()


def test_ac07_stage_two_requires_stage_one(tmp_path):
    wf = make_workflow(tmp_path)
    result = wf.prepare_draft({"facture_id": "FAC-012", "palier": 2})
    assert result["ok"] is False
    assert "palier 1" in result["erreur"].lower()


def test_ac08_idempotency_prevents_duplicate_record(tmp_path):
    wf = make_workflow(tmp_path)
    draft_id, validation_id = create_approved_reminder(wf)
    args = {
        "brouillon_id": draft_id,
        "validation_id": validation_id,
        "cle_idempotence": "fac001-stage1-test-key",
    }
    first = wf.record_simulated_reminder(args)
    second = wf.record_simulated_reminder(args)
    assert first["ok"] is True
    assert second["status"] == "already_recorded"
    assert len(wf.snapshot()["recorded_reminders"]) == 1
    # Même facture/palier avec une autre clé : le doublon reste interdit.
    duplicate = wf.record_simulated_reminder({**args, "cle_idempotence": "different-key"})
    assert duplicate["ok"] is False
    assert len(wf.snapshot()["recorded_reminders"]) == 1


def test_ac09_unknown_tool_is_blocked_and_logged(tmp_path):
    wf = make_workflow(tmp_path)
    result = execute_tool("delete_all_invoices", {}, wf)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert wf.snapshot()["blocked_tools"][-1]["name"] == "delete_all_invoices"


def test_ac10_step_limit_is_controlled(tmp_path):
    wf = make_workflow(tmp_path)
    result = run_agent(max_steps=1, workflow=wf)
    assert result.status == "max_steps_reached"
    assert result.steps == 1


def test_ac11_resume_from_persisted_pending_approval(tmp_path):
    state_path = tmp_path / "state.json"
    first_process = LocalWorkflow(state_path=state_path)
    draft = first_process.prepare_draft({"facture_id": "FAC-001", "palier": 1})
    draft_id = draft["brouillon"]["brouillon_id"]
    request = first_process.submit_for_approval({"brouillon_id": draft_id})
    validation_id = request["validation"]["validation_id"]

    # Simulation d'une interruption : nouvelle instance, même fichier d'état.
    resumed_process = LocalWorkflow(state_path=state_path)
    pending = resumed_process.submit_for_approval({"brouillon_id": draft_id})
    assert pending["validation"]["validation_id"] == validation_id
    assert resumed_process.approve(validation_id, "valideur-reprise")["ok"] is True
    args = {
        "brouillon_id": draft_id,
        "validation_id": validation_id,
        "cle_idempotence": "resume-fac001-stage1",
    }
    first = resumed_process.record_simulated_reminder(args)
    second = resumed_process.record_simulated_reminder(args)
    assert first["ok"] is True
    assert second["status"] == "already_recorded"
    assert len(resumed_process.snapshot()["recorded_reminders"]) == 1


