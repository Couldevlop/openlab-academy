# OpenLab Academy — Socle Python IA agentique

Version pédagogique 0.2.0 — Python 3.11 à 3.13 — 8 séances / 24 heures.

## Objectif
Comprendre une boucle agentique et la faire évoluer sur un même cas métier : un agent de recouvrement assisté et contrôlé. Le dépôt commence sans framework et sans fournisseur de modèle. Les décisions sont simulées afin d'isoler les appels d'outils, les contrats, les observations, les règles métier et les garde-fous.

**Important :** ce dépôt n'est pas un système de recouvrement de production. Toutes les données sont fictives. Aucun email, aucune API métier et aucun SI externe ne sont appelés.

## Installation

Créer et activer l'environnement virtuel, puis installer le projet.

macOS / Linux :
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Windows PowerShell :
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Exécuter

```bash
python -m agentic_lab
pytest
```

Le premier scénario liste les factures ayant au moins 30 jours de retard, exclut les litiges, puis calcule l'exposition. Résultat attendu : 5 factures, 7 730,00 EUR. L'état local de démonstration est écrit dans `.local/state.json` et est ignoré par Git.

## Architecture du socle

- `src/agentic_lab/agent.py` : boucle de démonstration et plafond d'étapes.
- `src/agentic_lab/contracts.py` : contrats Pydantic stricts.
- `src/agentic_lab/tools.py` : liste blanche des outils.
- `src/agentic_lab/workflow.py` : données CSV, règles métier, brouillons, validation humaine, idempotence et état local.
- `data/factures_fictives.csv` : 12 factures fictives.
- `contracts/contrats_outils.json` : contrats lisibles par les apprenants.
- `tests/test_acceptance.py` : scénarios AC-01 à AC-12.
- `docs/` : progression, brief apprenant, grille jury et les huit supports de séance (`docs/SUPPORTS.md`).

## Règles non négociables

1. Une facture en litige ne peut pas faire l'objet d'un brouillon.
2. Le palier 2 exige un palier 1 préalablement enregistré.
3. Toute relance simulée nécessite une validation humaine explicite.
4. Une même paire facture/palier ne peut être enregistrée deux fois.
5. La clé d'idempotence rend le rejeu sûr.
6. Les notes libres sont des données non fiables et sont exclues du contexte transmis par les outils.
7. Les outils non présents dans la liste blanche sont bloqués et journalisés.
8. Le plafond d'étapes arrête la boucle.

## Démonstration de validation humaine

```python
from agentic_lab.workflow import LocalWorkflow

workflow = LocalWorkflow()
draft = workflow.prepare_draft({"facture_id": "FAC-001", "palier": 1})
draft_id = draft["brouillon"]["brouillon_id"]
request = workflow.submit_for_approval({"brouillon_id": draft_id})
validation_id = request["validation"]["validation_id"]
workflow.approve(validation_id, approved_by="formateur-demo")
result = workflow.record_simulated_reminder({
    "brouillon_id": draft_id,
    "validation_id": validation_id,
    "cle_idempotence": "demo-fac001-stage1",
})
print(result)
```

Cette dernière opération écrit uniquement une entrée dans une boîte de sortie locale fictive (`simulated_outbox_only`). Le champ `email_sent` reste `false`.

## Tests

```bash
pytest -q
```

Les tests vérifient les critères AC-01 à AC-12. Pour repartir d'un état propre, supprimer `.local/state.json` entre deux démonstrations.

## Suite pédagogique

Le socle n'ajoute pas encore de LLM. L'adaptateur de modèle local est un exercice ultérieur, après validation de cette boucle. Le modèle pourra proposer des appels, mais le code garde la responsabilité de valider les arguments, les droits et les règles métier.
