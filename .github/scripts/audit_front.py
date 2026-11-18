"""Audit des dependances de production du front, avec exceptions datees et justifiees.

`npm audit` echoue des qu'un avis de severite haute existe, meme quand l'amont n'a
publie aucune version corrigee : la chaine reste alors rouge sans qu'aucun geste ne
puisse la rendre verte. Ce controle garde la meme exigence, et ne tolere un avis que
s'il est inscrit dans exceptions-audit.json, qu'il n'a pas de correctif disponible, et
que sa date de revue n'est pas depassee.

Usage : python .github/scripts/audit_front.py [dossier du front]
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

SEVERITES = {"high", "critical"}
IDENTIFIANT = re.compile(r"^GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}$")
HORIZON_MAXIMAL = 180  # jours : une tolerance ne peut pas etre reportee indefiniment


def _echec(message: str, detail: str = "") -> None:
    print(message)
    if detail:
        print(detail[:2000])
    raise SystemExit(1)


def _audit(dossier: pathlib.Path) -> dict:
    """Le rapport de npm audit, ou l'echec : un audit qui n'a pas tourne ne laisse rien passer."""
    if not (dossier / "package-lock.json").is_file():
        _echec(f"Aucun package-lock.json dans {dossier} : l'audit ne porterait sur rien.")
    execution = subprocess.run(
        ["npm", "audit", "--omit=dev", "--json"],
        cwd=dossier, capture_output=True, text=True, shell=sys.platform == "win32",
    )
    # npm rend 0 sans faille et 1 avec ; tout autre code signale un audit qui n'a pas tourne
    if execution.returncode not in (0, 1):
        _echec(f"npm audit a termine avec le code {execution.returncode} :",
               execution.stderr or execution.stdout)
    try:
        rapport = json.loads(execution.stdout)
    except json.JSONDecodeError:
        _echec("npm audit n'a pas rendu de JSON exploitable :", execution.stdout)
    if not isinstance(rapport, dict) or "vulnerabilities" not in rapport or "error" in rapport:
        _echec("npm audit n'a pas rendu un rapport complet :", execution.stdout)
    return rapport


def _avis(rapport: dict) -> dict[str, dict]:
    """Les avis de severite haute, par identifiant GHSA."""
    trouves = {}
    for paquet, faille in (rapport.get("vulnerabilities") or {}).items():
        for via in faille.get("via") or []:
            if not isinstance(via, dict) or via.get("severity") not in SEVERITES:
                continue
            identifiant = (via.get("url") or "").rstrip("/").split("/")[-1]
            trouves.setdefault(identifiant, {
                "titre": via.get("title", ""),
                "plage": via.get("range", ""),
                "severite": via.get("severity"),
                "paquets": set(),
                "correctif": faille.get("fixAvailable"),
            })
            trouves[identifiant]["paquets"].add(paquet)
            if via.get("severity") == "critical":
                trouves[identifiant]["severite"] = "critical"
            # un seul paquet qui annonce un correctif sans rupture suffit a rendre l'avis corrigeable
            if _correctif_sans_rupture(faille.get("fixAvailable")):
                trouves[identifiant]["correctif"] = faille.get("fixAvailable")
    return trouves


def _inexpliques(rapport: dict) -> list[str]:
    """Les paquets de severite haute qu'aucun avis du rapport n'explique.

    npm decrit une faille soit par un avis (un objet dans « via »), soit par le nom du
    paquet dont elle est heritee (une chaine). Un paquet dont la chaine ne mene a aucun
    avis du rapport echapperait au controle : il est refuse.
    """
    failles = rapport.get("vulnerabilities") or {}
    inexpliques = []
    for nom, faille in sorted(failles.items()):
        if faille.get("severity") not in SEVERITES:
            continue
        liens = faille.get("via") or []
        if not liens:
            inexpliques.append(f"{nom} : severite haute sans avis ni origine")
            continue
        for via in liens:
            if isinstance(via, dict):
                continue
            if isinstance(via, str) and via in failles:
                continue
            inexpliques.append(f"{nom} : origine « {via} » absente du rapport")
    # recoupement avec les compteurs de npm : un avis qui echappe au parcours se voit ici
    compteurs = (rapport.get("metadata") or {}).get("vulnerabilities") or {}
    attendus = sum(compteurs.get(severite, 0) for severite in SEVERITES)
    comptes = sum(1 for f in failles.values() if f.get("severity") in SEVERITES)
    if attendus != comptes:
        inexpliques.append(f"npm annonce {attendus} paquets de severite haute, {comptes} lus")
    return inexpliques


def _correctif_sans_rupture(correctif) -> bool:
    """Un correctif applicable sans changement majeur. Toute forme inconnue est tenue pour tel."""
    if correctif is True:
        return True
    if correctif is False or correctif is None:
        return False
    if isinstance(correctif, dict):
        return not correctif.get("isSemVerMajor")
    return True


def _declares(exception: dict) -> set[str]:
    """Les paquets que la tolerance couvre : « paquet », ou la liste « paquets »."""
    declares = exception.get("paquets") or [exception.get("paquet")]
    return {str(nom) for nom in declares if nom}


def _exceptions(fichier: pathlib.Path, aujourdhui: datetime.date) -> dict[str, dict]:
    """Les tolerances declarees. Une entree mal formee fait echouer le controle, pas passer l'avis."""
    if not fichier.is_file():
        return {}
    try:
        declarees = json.loads(fichier.read_text(encoding="utf-8"))["exceptions"]
    except (json.JSONDecodeError, KeyError, TypeError) as erreur:
        _echec(f"{fichier} est illisible : {erreur}")
    retenues = {}
    for entree in declarees:
        identifiant = str(entree.get("avis", ""))
        if not IDENTIFIANT.match(identifiant):
            _echec(f"{fichier} : identifiant d'avis invalide, « {identifiant} »")
        for champ in ("paquet", "raison"):
            if not str(entree.get(champ, "")).strip():
                _echec(f"{fichier} : {identifiant} n'a pas de « {champ} »")
        try:
            revue = datetime.date.fromisoformat(str(entree.get("revoir_avant", "")))
        except ValueError:
            _echec(f"{fichier} : {identifiant} n'a pas de date de revue au format AAAA-MM-JJ")
        if (revue - aujourdhui).days > HORIZON_MAXIMAL:
            _echec(f"{fichier} : {identifiant} est reporte au {revue}, "
                   f"au-dela des {HORIZON_MAXIMAL} jours admis")
        retenues[identifiant] = {**entree, "revoir_avant": revue}
    return retenues


def main() -> int:
    dossier = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "apps/openlab_academy/frontend")
    aujourdhui = datetime.date.today()
    exceptions = _exceptions(dossier / "exceptions-audit.json", aujourdhui)

    rapport = _audit(dossier)
    avis = _avis(rapport)
    refus = _inexpliques(rapport)
    for identifiant, detail in sorted(avis.items()):
        paquets = ", ".join(sorted(detail["paquets"]))
        if not IDENTIFIANT.match(identifiant):
            refus.append(f"avis sans identifiant exploitable ({paquets}) : {detail['titre']}")
            continue
        exception = exceptions.get(identifiant)
        if exception is None:
            refus.append(f"{identifiant} ({paquets}) : {detail['titre']}, aucune exception declaree")
            continue
        if detail["severite"] == "critical":
            refus.append(f"{identifiant} ({paquets}) : avis critique, aucune tolerance possible")
            continue
        revue = exception["revoir_avant"]
        if revue < aujourdhui:
            refus.append(f"{identifiant} ({paquets}) : exception expiree le {revue}, a reexaminer")
        elif _correctif_sans_rupture(detail["correctif"]):
            refus.append(f"{identifiant} ({paquets}) : un correctif existe desormais, mettez a jour")
        elif detail["paquets"] - _declares(exception):
            hors = ", ".join(sorted(detail["paquets"] - _declares(exception)))
            refus.append(f"{identifiant} : l'avis touche desormais {hors}, hors du perimetre tolere")
        else:
            print(f"  tolere   {identifiant}  {paquets}  revue avant le {revue}")
            print(f"           {exception['raison']}")

    if refus:
        print("\nAudit en echec :")
        for ligne in refus:
            print("  " + ligne)
        return 1
    print(f"\nAudit du front : {len(avis)} avis de severite haute, tous tolerees et datees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
