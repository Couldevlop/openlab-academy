"""Verse les journaux normalisés dans l'index du SIEM, puis s'arrête.

Lancé par `docker-compose up` ; il tourne dans le conteneur `chargeur`, qui voit le dossier du lab
en lecture seule. Il appelle **votre** `normaliser.py` : tant que `lire_annuaire` n'est pas écrit,
le chargement s'arrête dessus, et c'est voulu — un SIEM qui ignore l'annuaire ne voit pas la moitié
d'une intrusion.
"""
import json
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/lab")

INDEX = "http://journal:9200/evenements"
LOT = 500


def attendre_le_journal(essais: int = 60) -> None:
    for reste in range(essais, 0, -1):
        try:
            urllib.request.urlopen("http://journal:9200", timeout=2).read()
            return
        except (urllib.error.URLError, OSError):
            time.sleep(2)
    raise SystemExit("le journal n'a pas répondu : `docker-compose logs journal`")


def verser(evenements: list[dict]) -> None:
    """Envoi par lots, au format « bulk » : une ligne d'entête, une ligne de document."""
    for debut in range(0, len(evenements), LOT):
        corps = ""
        for evenement in evenements[debut:debut + LOT]:
            plat = {**evenement, **evenement.pop("details")}
            corps += json.dumps({"index": {}}) + "\n" + json.dumps(plat, ensure_ascii=False) + "\n"
        requete = urllib.request.Request(f"{INDEX}/_bulk", data=corps.encode("utf-8"),
                                         headers={"Content-Type": "application/x-ndjson"})
        urllib.request.urlopen(requete, timeout=30).read()
        print(f"  {min(debut + LOT, len(evenements))}/{len(evenements)}")


def main() -> None:
    attendre_le_journal()
    try:
        from normaliser import collecter
    except ImportError as manque:
        raise SystemExit(f"normaliser.py introuvable : {manque}")

    try:
        evenements = collecter()
    except NotImplementedError as manque:
        raise SystemExit(f"Collecte incomplète : {manque}. Écrivez lire_annuaire, puis relancez.")

    print(f"{len(evenements)} événements à verser")
    verser(evenements)
    print("Index « evenements » prêt. Console : http://localhost:5601 "
          "(Dashboards → Discover → créer la vue « evenements », champ temps « horodatage »).")


if __name__ == "__main__":
    main()
