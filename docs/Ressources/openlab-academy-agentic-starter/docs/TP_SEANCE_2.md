# TP séance 2 — Construire une boucle d'agent avec des outils Python

## Objectif
Comprendre la frontière entre décision, appel d'outil, validation, exécution et observation. Le scénario initial
est déterministe : il simule les décisions du modèle pour isoler la mécanique.

## Prérequis
- Cadrage de la séance 1 rendu.
- Socle installé et vert sur le poste de l'apprenant :

```bash
python -m venv .venv            # Windows : py -3.12 -m venv .venv
source .venv/bin/activate       # Windows : .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q                       # attendu : 16 passed
python -m agentic_lab            # attendu : 5 factures, 7 730,00 EUR
```

## Déroulé indicatif — 3 heures
1. 0–15 min : objectif, agent vs outil vs workflow.
2. 15–40 min : lecture de `agent.py`, `tools.py`, `contracts.py`.
3. 40–60 min : tracer un appel de recherche et son observation.
4. 60–70 min : pause.
5. 70–105 min : ajouter un filtre ou un outil de calcul.
6. 105–135 min : écrire des tests nominaux et des cas invalides.
7. 135–160 min : tester un outil non autorisé et le plafond d'étapes.
8. 160–175 min : expliquer la validation humaine et l'idempotence.
9. 175–180 min : quiz de sortie.

## Défi apprenant
1. Ajouter un filtre `montant_min_eur` à l'outil de recherche.
2. Mettre à jour le contrat JSON et le modèle Pydantic.
3. Ajouter au moins trois tests : cas nominal, montant négatif, argument supplémentaire.
4. Montrer qu'une note malveillante du CSV ne peut pas modifier les règles.

## Indices graduels
- *Indice 1* : `ListInvoicesArgs` refuse déjà tout argument inconnu (`extra="forbid"`) ; un argument en trop doit
  donc produire une erreur d'arguments, pas une exception.
- *Indice 2* : un montant négatif se refuse dans le contrat (`Field(ge=0)`), pas dans le corps de l'outil.
- *Indice 3* : `list_invoices` retire `note_non_fiable` de chaque ligne avant de répondre ; vérifier ce qui sort de
  l'outil, pas ce qui est dans le CSV.

## Livrables
- code modifié ;
- tests verts ;
- schéma d'appel d'outil ;
- explication orale de 2 minutes sur la liste blanche et la validation des arguments.

## Contrôle de fin de séance
`pytest -q` passe avec les nouveaux tests, et l'apprenant sait montrer dans le code *où* un argument venu du modèle
est refusé avant toute exécution.
