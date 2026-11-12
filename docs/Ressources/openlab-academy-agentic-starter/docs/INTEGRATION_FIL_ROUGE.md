# Intégration du projet fil rouge — version 0.2.0

Le CSV, les contrats et les critères d'acceptation du projet fil rouge ont été intégrés au socle `agentic_lab`.

## Périmètre réellement exécutable
- Recherche et calcul d'exposition depuis le CSV.
- Blocage des factures en litige.
- Brouillons locaux sans envoi.
- Demande de validation et validation humaine simulée.
- Enregistrement dans une boîte de sortie locale fictive après approbation.
- Idempotence, journal d'événements, blocage des outils inconnus et plafond d'étapes.
- Reprise de l'état après recréation du service à partir du même fichier JSON.

## Limites
- Pas de LLM dans cette version : la boucle est déterministe.
- Pas de serveur MCP/A2A dans cette version.
- L'approbation humaine est simulée par un appel explicite à `approve()` ; il n'existe pas encore d'interface utilisateur ni d'authentification.
- Le stockage JSON local sert à l'apprentissage ; il ne remplace pas une base transactionnelle.
- Pas de concurrence multi-processus ni de garanties de production.

## Validation locale
Depuis la racine :

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m agentic_lab
```
