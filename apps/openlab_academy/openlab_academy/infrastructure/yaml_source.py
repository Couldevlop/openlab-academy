"""Adaptateur d'entrée : fichiers YAML de parcours -> entités du domaine."""
import pathlib
import re

import yaml

from openlab_academy.domain.grille import Grille, GrilleInvalide
from openlab_academy.domain.parcours import (Annonce, Bloc, Extrait, Figure, Module, Niveau, Parcours,
                                             ParcoursInvalide, Projet, Question, Section, Tableau)
from openlab_academy.domain.reglages import Reglages, ReglagesInvalides
from openlab_academy.domain.reglages_evaluation import Chaine

PARCOURS_DIR = pathlib.Path(__file__).parents[1] / "data" / "parcours"
_NOM_ARCHIVE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.zip")
_NOM_IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.(?:jpg|jpeg|png|webp|svg)")
_LISTES_PROJET = ("objectifs", "fonctionnalites", "stack", "criteres_acceptation", "livrables")
# Paramètres qu'un parcours peut surcharger : clé YAML -> champ du domaine Parcours
_PARAMETRES = {"projets_par_portfolio": "projets_attendus", "heures_par_module": "heures_par_module"}


def _entier(valeur) -> bool:
    return isinstance(valeur, int) and not isinstance(valeur, bool)


class FormatInvalide(ValueError):
    """Fichier de parcours mal formé ou contraire aux invariants du domaine."""


class _Lecteur:
    def __init__(self, source: str, reglages: Reglages):
        self.source = source
        self.reglages = reglages

    def parametres(self, d: dict) -> dict:
        valeurs = {"projets_attendus": self.reglages.projets_par_portfolio,
                   "heures_par_module": self.reglages.heures_par_module,
                   "questions_par_quiz": self.reglages.questions_par_quiz}
        surcharges = d.get("parametres") or {}
        if not isinstance(surcharges, dict):
            raise FormatInvalide(f"{self.source}: parametres doit être un dictionnaire")
        for cle, valeur in surcharges.items():
            if cle not in _PARAMETRES:
                raise FormatInvalide(f"{self.source}: parametres.{cle} inconnu ({sorted(_PARAMETRES)})")
            if not _entier(valeur):
                raise FormatInvalide(f"{self.source}: parametres.{cle} doit être un entier")
            valeurs[_PARAMETRES[cle]] = valeur
        return valeurs

    def booleen(self, d: dict, cle: str) -> bool:
        valeur = d.get(cle, False)
        if not isinstance(valeur, bool):
            raise FormatInvalide(f"{self.source}: {cle} doit être un booléen")
        return valeur

    def exiger(self, obj: dict, champ: str, chemin: str):
        valeur = obj.get(champ)
        if valeur in (None, "", []):
            raise FormatInvalide(f"{self.source}: {chemin}{champ} manquant")
        return valeur

    def textes(self, valeurs, chemin: str) -> tuple[str, ...]:
        for i, v in enumerate(valeurs):
            if not isinstance(v, str):
                raise FormatInvalide(f"{self.source}: {chemin}[{i}] doit être un texte (« : » non quoté ?)")
        return tuple(valeurs)

    def question(self, q, chemin: str) -> Question:
        if not isinstance(q, dict):
            raise FormatInvalide(f"{self.source}: {chemin} doit être une question (dictionnaire)")
        bonnes = self.exiger(q, "bonnes", chemin)
        if not isinstance(bonnes, list) or not all(_entier(b) for b in bonnes):
            raise FormatInvalide(f"{self.source}: {chemin}bonnes doit être une liste de numéros d'options")
        return Question(enonce=str(self.exiger(q, "question", chemin)),
                        options=self.textes(self.exiger(q, "options", chemin), f"{chemin}options"),
                        bonnes=tuple(bonnes), explication=str(self.exiger(q, "explication", chemin)))

    def grille(self, brut, chemin: str) -> Grille | None:
        """Clé facultative `grille:` : liste de critères (code, libelle, poids, niveaux[, description, controles])."""
        if brut is None:
            return None
        if not isinstance(brut, list):
            raise FormatInvalide(f"{self.source}: {chemin} doit être une liste de critères")
        try:
            return Grille.depuis_dict({"criteres": [self._critere(c, f"{chemin}[{i}]") for i, c in enumerate(brut)]})
        except GrilleInvalide as e:
            raise FormatInvalide(f"{self.source}: {chemin} invalide : {e}") from None

    def _critere(self, c, chemin: str) -> dict:
        if not isinstance(c, dict):
            raise FormatInvalide(f"{self.source}: {chemin} doit être un critère (dictionnaire)")
        niveaux = self.exiger(c, "niveaux", f"{chemin}.")
        if not isinstance(niveaux, list) or not all(isinstance(n, dict) and "libelle" in n for n in niveaux):
            raise FormatInvalide(f"{self.source}: {chemin}.niveaux doit être une liste de niveaux avec un libelle")
        if not _entier(c.get("poids")):
            raise FormatInvalide(f"{self.source}: {chemin}.poids doit être un entier")
        libelle = str(self.exiger(c, "libelle", f"{chemin}."))
        return {"code": str(self.exiger(c, "code", f"{chemin}.")), "libelle": libelle, "poids": c["poids"],
                "description": str(c.get("description") or libelle),
                "controles": self.textes(c.get("controles") or (), f"{chemin}.controles"),
                "niveaux": [{"libelle": str(n["libelle"]), "descripteur": str(n.get("descripteur") or n["libelle"]),
                             "points": n.get("points", i)} for i, n in enumerate(niveaux)]}

    def correction(self, brut, chemin: str) -> Chaine | None:
        """Clé facultative `correction:` : chaîne d'étapes propre à l'exercice (voir Chaine.depuis_dict)."""
        if brut is None:
            return None
        try:
            return Chaine.depuis_dict(brut)
        except ReglagesInvalides as e:
            raise FormatInvalide(f"{self.source}: {chemin} invalide : {e}") from None

    def archive(self, brut, chemin: str) -> str:
        """Clé facultative `archive:` : nom de fichier seul d'une archive à joindre à la leçon. Jamais un chemin
        (OWASP A01 : le fichier est lu dans le dossier des ressources de l'application, pas où le texte l'indique)."""
        if brut is None:
            return ""
        nom = str(brut)
        if not _NOM_ARCHIVE.fullmatch(nom):
            raise FormatInvalide(f"{self.source}: {chemin} doit être un nom de fichier .zip sans chemin")
        return nom

    def couverture(self, brut, chemin: str = "couverture") -> str:
        """Clé facultative `couverture:` : nom de fichier seul d'une image livrée avec l'application. Jamais un
        chemin (OWASP A01 : l'image est lue dans le dossier des ressources, pas où le texte l'indique)."""
        if brut is None:
            return ""
        nom = str(brut)
        if not _NOM_IMAGE.fullmatch(nom):
            raise FormatInvalide(f"{self.source}: {chemin} doit être un nom d'image sans chemin "
                                 "(.jpg, .jpeg, .png, .webp ou .svg)")
        return nom

    def _entrees(self, brut, chemin: str) -> list[dict]:
        """Une liste de dictionnaires, ou rien. Le message nomme la clé pour qu'un fichier de contenu se
        corrige sans ouvrir le code."""
        if brut is None:
            return []
        if not isinstance(brut, list) or any(not isinstance(e, dict) for e in brut):
            raise FormatInvalide(f"{self.source}: {chemin} doit être une liste de dictionnaires")
        return brut

    def _construire(self, fabrique, chemin: str, **champs):
        """Les invariants restent dans le domaine ; le lecteur se borne à situer l'erreur dans le fichier."""
        try:
            return fabrique(**champs)
        except ParcoursInvalide as e:
            raise FormatInvalide(f"{self.source}: {chemin} invalide : {e}") from None

    def figures(self, brut, chemin: str) -> tuple[Figure, ...]:
        return tuple(
            self._construire(Figure, f"{chemin}[{i}]", nom=str(f.get("nom") or ""),
                             legende=str(f.get("legende") or ""))
            for i, f in enumerate(self._entrees(brut, chemin)))

    def tableaux(self, brut, chemin: str) -> tuple[Tableau, ...]:
        resultat = []
        for i, t in enumerate(self._entrees(brut, chemin)):
            lignes = t.get("lignes")
            if not isinstance(lignes, list) or any(not isinstance(l, list) for l in lignes):
                raise FormatInvalide(f"{self.source}: {chemin}[{i}].lignes doit être une liste de listes")
            resultat.append(self._construire(
                Tableau, f"{chemin}[{i}]", titre=str(t.get("titre") or ""),
                entetes=tuple(str(c) for c in (t.get("entetes") or ())),
                lignes=tuple(tuple(str(c) for c in ligne) for ligne in lignes)))
        return tuple(resultat)

    def extraits(self, brut, chemin: str) -> tuple[Extrait, ...]:
        return tuple(
            self._construire(Extrait, f"{chemin}[{i}]", titre=str(e.get("titre") or ""),
                             langage=str(e.get("langage") or ""), code=str(e.get("source") or ""))
            for i, e in enumerate(self._entrees(brut, chemin)))

    def sections(self, brut, chemin: str) -> tuple[Section, ...]:
        """Clé facultative `cours:` : le chapitre en sections titrées. Le texte d'une section se découpe en
        paragraphes sur les sauts de ligne, comme les travaux pratiques : un scalaire YAML replié (>-)
        réduit déjà une ligne vide à un simple saut."""
        resultat = []
        for i, s in enumerate(self._entrees(brut, chemin)):
            ou = f"{chemin}[{i}]"
            paragraphes = tuple(p.strip() for p in re.split(r"\n+", str(s.get("texte") or "")) if p.strip())
            resultat.append(self._construire(
                Section, ou, titre=str(s.get("titre") or ""), paragraphes=paragraphes,
                figures=self.figures(s.get("figures"), f"{ou}.figures"),
                tableaux=self.tableaux(s.get("tableaux"), f"{ou}.tableaux"),
                extraits=self.extraits(s.get("code"), f"{ou}.code")))
        return tuple(resultat)

    def module(self, m: dict, chemin: str) -> Module:
        quiz = m.get("quiz") or []
        if not isinstance(quiz, list):
            raise FormatInvalide(f"{self.source}: {chemin}quiz doit être une liste de questions")
        return Module(*(str(self.exiger(m, c, chemin)) for c in ("num", "title", "contenu", "livrable")),
                      quiz=tuple(self.question(q, f"{chemin}quiz[{i}].") for i, q in enumerate(quiz)),
                      mise_en_situation=str(m.get("mise_en_situation") or ""),
                      travaux_pratiques=str(m.get("travaux_pratiques") or ""),
                      archive=self.archive(m.get("archive"), f"{chemin}archive"),
                      cours=self.sections(m.get("cours"), f"{chemin}cours"),
                      figures=self.figures(m.get("figures"), f"{chemin}figures"),
                      tableaux=self.tableaux(m.get("tableaux"), f"{chemin}tableaux"),
                      extraits=self.extraits(m.get("code"), f"{chemin}code"),
                      grille_cas=self.grille(m.get("grille_mise_en_situation"), f"{chemin}grille_mise_en_situation"),
                      correction_cas=self.correction(m.get("correction_mise_en_situation"),
                                                     f"{chemin}correction_mise_en_situation"),
                      grille_livrable=self.grille(m.get("grille_livrable"), f"{chemin}grille_livrable"),
                      correction_livrable=self.correction(m.get("correction_livrable"),
                                                          f"{chemin}correction_livrable"))

    def projet(self, p: dict, chemin: str, portfolio: bool) -> Projet:
        listes = {c: self.textes(self.exiger(p, c, chemin), f"{chemin}{c}") for c in _LISTES_PROJET}
        if "exigences_specifiques" not in p:
            raise FormatInvalide(f"{self.source}: {chemin}exigences_specifiques manquant")
        niveau = self.exiger(p, "niveau", chemin)
        try:
            niveau = Niveau(niveau)
        except ValueError:
            raise FormatInvalide(f"{self.source}: {chemin}niveau '{niveau}' inconnu") from None
        duree = self.exiger(p, "duree_h", chemin)
        if not _entier(duree):
            raise FormatInvalide(f"{self.source}: {chemin}duree_h doit être un entier")
        apres = p.get("apres_module")
        return Projet(
            titre=str(self.exiger(p, "titre", chemin)), duree_h=duree, niveau=niveau,
            contexte=str(self.exiger(p, "contexte", chemin)),
            exigences_specifiques=self.textes(p["exigences_specifiques"] or (), f"{chemin}exigences_specifiques"),
            apres_module=None if apres is None else str(apres),
            cours=self.sections(p.get("cours"), f"{chemin}cours"),
            figures=self.figures(p.get("figures"), f"{chemin}figures"),
            tableaux=self.tableaux(p.get("tableaux"), f"{chemin}tableaux"),
            extraits=self.extraits(p.get("code"), f"{chemin}code"),
            grille=self.grille(p.get("grille"), f"{chemin}grille"),
            correction=self.correction(p.get("correction"), f"{chemin}correction"), **listes,
        )

    def annonce(self, d: dict) -> Annonce:
        return Annonce(
            title=str(self.exiger(d, "title", "")),
            short_introduction=str(self.exiger(d, "short_introduction", "")),
            description=str(self.exiger(d, "description", "")),
            tags=self.textes(d.get("tags") or (), "tags"), card_gradient=str(d.get("card_gradient", "Blue")),
            couverture=self.couverture(d.get("couverture")),
        )

    def element(self, d) -> "Parcours | Annonce":
        if not isinstance(d, dict):
            raise FormatInvalide(f"{self.source}: le fichier doit contenir un parcours (dictionnaire)")
        statut = d.get("statut", "complet")
        if statut == "a_venir":
            return self.annonce(d)
        if statut != "complet":
            raise FormatInvalide(f"{self.source}: statut « {statut} » inconnu (complet | a_venir)")
        return self.parcours(d)

    def parcours(self, d) -> Parcours:
        blocs = tuple(
            Bloc(str(self.exiger(b, "title", f"blocs[{i}].")),
                 tuple(self.module(m, f"blocs[{i}].modules[{j}].")
                       for j, m in enumerate(self.exiger(b, "modules", f"blocs[{i}]."))))
            for i, b in enumerate(self.exiger(d, "blocs", "")))
        parametres = self.parametres(d)
        projets = self.exiger(d, "portfolio", "") if parametres["projets_attendus"] > 0 else d.get("portfolio") or ()
        portfolio = tuple(self.projet(p, f"portfolio[{k}].", True) for k, p in enumerate(projets))
        return Parcours(
            title=str(self.exiger(d, "title", "")),
            short_introduction=str(self.exiger(d, "short_introduction", "")),
            description=str(self.exiger(d, "description", "")),
            tags=self.textes(d.get("tags") or (), "tags"), card_gradient=str(d.get("card_gradient", "Blue")),
            couverture=self.couverture(d.get("couverture")),
            blocs=blocs, portfolio=portfolio,
            capstone=self.projet(self.exiger(d, "capstone", ""), "capstone.", False),
            gratuit=self.booleen(d, "gratuit"),
            acces_limite_a_la_cohorte=self.booleen(d, "acces_limite_a_la_cohorte"),
            mise_en_avant=self.booleen(d, "mise_en_avant"),
            **parametres,
        )


def depuis_dict(d, source: str, reglages: Reglages = Reglages()) -> Parcours | Annonce:
    try:
        return _Lecteur(source, reglages).element(d)
    except ParcoursInvalide as e:
        raise FormatInvalide(f"{source}: {e}") from e


def charger_dossier(dossier: pathlib.Path, reglages: Reglages = Reglages()) -> list[Parcours | Annonce]:
    lot = []
    for fichier in sorted(dossier.glob("*.yaml")):
        try:
            data = yaml.safe_load(fichier.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise FormatInvalide(f"{fichier.name}: YAML invalide ou non sûr ({e.__class__.__name__})") from e
        lot.append(depuis_dict(data, fichier.name, reglages))
    return lot
