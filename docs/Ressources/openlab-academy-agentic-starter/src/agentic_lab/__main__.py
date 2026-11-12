from agentic_lab.agent import run_agent
from agentic_lab.config import load_settings


def main() -> None:
    settings = load_settings()
    print("OpenLab Academy | Projet fil rouge — agent de recouvrement contrôlé")
    print(f"Mode={settings.model_provider!r} | plafond={settings.max_steps} étape(s)")
    print("Données fictives ; aucune connexion externe ; aucun email envoyé.")
    print("-" * 72)
    result = run_agent(max_steps=settings.max_steps)
    for item in result.observations:
        print(f"[étape {item['step']}] {item['tool']} -> {item['result']}")
    print("\nRÉSULTAT FINAL")
    print(result.final_text)
    print(f"Statut : {result.status}")


if __name__ == "__main__":
    main()
