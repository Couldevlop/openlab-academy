# Rapport de validation technique — socle 0.2.0

## Environnement de vérification
- Python : 3.13.5
- Pydantic : 2.13.5
- pytest : 9.0.2
- Système de test : environnement local du générateur de pack

## Résultats
- `pytest -q` : **16 tests réussis**.
- `python -m compileall -q src tests` : réussite.
- `python -m agentic_lab` : exécution réussie ; 5 factures éligibles, exposition de 7 730 000 F CFA, aucun envoi.
- Scénario à 60 jours : 2 factures, 4 990 000 F CFA.
- Validation/reprise : test d'interruption après demande d'approbation, réouverture de l'état JSON, approbation et enregistrement simulé sans doublon.

## Limites de cette validation
- Python 3.11 et 3.12 n'ont pas été exécutés dans cet environnement ; ils restent les versions recommandées pour la cohorte si elles sont disponibles sur les postes.
- Ruff n'était pas installé dans l'environnement de validation ; le lint n'est donc pas déclaré réussi.
- Aucun fournisseur LLM, Ollama, serveur MCP ou A2A n'est branché dans cette version.
- L'état JSON local et l'approbation simulée sont pédagogiques ; ce n'est pas un mécanisme de production ou une authentification réelle.

## Validation sur poste formateur — 12 novembre 2026

Critère de sortie du compte rendu opérationnel n° 3 : installation et exécution confirmées sur le poste du
formateur.

- Python : 3.12.6 (Windows), environnement virtuel dédié `.venv`.
- `py -3.12 -m venv .venv` puis `pip install -e ".[dev]"` : réussis.
- `pytest -q` : **16 tests réussis**.
- `python -m agentic_lab` : 5 factures éligibles, exposition de 7 730 000 F CFA, aucune relance envoyée, statut
  `completed`.
- `ruff check .` : **All checks passed**. Huit écarts corrigés (tri des imports, `Callable` importé de
  `collections.abc`, alias `datetime.UTC`) ; la capture large de `tools.execute_tool` est conservée et documentée
  par un `noqa: BLE001` commenté, car elle constitue la frontière de sécurité qui transforme toute erreur d'outil
  en résultat contrôlé.

Écarts du rapport initial désormais levés : Python 3.12 est vérifié, et le lint est déclaré réussi. Python 3.11
reste la borne basse déclarée du socle, non exécutée ici.

## Commandes de reproduction
```bash
python -m pip install -e ".[dev]"
pytest -q
python -m agentic_lab
```

Le premier lancement avec état vierge crée `.local/state.json`. Supprimer ce fichier pour repartir d'un état pédagogique propre.
