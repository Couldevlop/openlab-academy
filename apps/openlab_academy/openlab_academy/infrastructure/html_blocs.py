"""Conversion entre les blocs EditorJS d'une rubrique et le HTML de l'éditeur riche qui la retouche.

Une partie de séance s'ouvre dans un champ Text Editor, qui travaille en HTML, alors que la leçon se rend en
blocs EditorJS. Deux sens, deux usages :

- `vers_html` pré-remplit l'éditeur à la publication ; la fidélité y est indifférente, puisque la leçon
  continue d'être assemblée depuis les blocs du fichier tant que la partie n'a pas été retouchée ;
- `vers_blocs` relit ce que l'administrateur a enregistré. C'est une frontière : le HTML qui entre vient d'un
  formulaire, donc rien n'y est accordé par défaut. Balises hors liste blanche effacées en conservant leur
  texte, attributs tous retirés sauf ceux attendus, adresses de liens et de médias limitées au site, tout
  texte réechappé (OWASP A03, échec fermé).

Les blocs qui citent un exercice (`assignment`, `quiz`) deviennent un repère : l'administrateur voit où le
devoir ou le quiz s'insère, et le repère revient en bloc à la relecture. Un type de bloc inattendu voyage dans
un attribut JSON plutôt que de disparaître.
"""
import html
import json
import re
from html.parser import HTMLParser

from openlab_academy.domain.parcours import LANGAGES

# balises de mise en forme autorisées dans un texte, avec les attributs qu'elles gardent
INLINE = {"b", "strong", "i", "em", "code", "a", "br"}
TITRES = {"h2": 2, "h3": 3, "h4": 4}
_LIEN = re.compile(r"/(?!/)[A-Za-z0-9._~+@%&=?/-]{0,400}")
_MEDIA = re.compile(r"/private/files/[A-Za-z0-9][A-Za-z0-9._-]{0,119}\.(?:svg|jpg|png|webp)")
_TYPE_DE_BLOC = re.compile(r"[a-zA-Z]{1,30}")
_CLE = re.compile(r"[a-z_]{1,30}")
_MARQUEURS = {"assignment": "Devoir", "quiz": "Quiz"}


def _e(texte: str) -> str:
    """Texte de bloc : même convention que `editorjs`, guillemets et apostrophes conservés."""
    return html.escape(texte, quote=False)


# --- blocs vers HTML ---------------------------------------------------------------------------------------------

def vers_html(blocs) -> str:
    """HTML de l'éditeur riche pour une suite de blocs EditorJS."""
    return "".join(_html_bloc(b) for b in blocs if isinstance(b, dict))


def _html_bloc(bloc: dict) -> str:
    type_ = bloc.get("type")
    data = bloc.get("data") or {}
    rendu = {"header": _html_titre, "paragraph": _html_paragraphe, "list": _html_liste,
             "table": _html_tableau, "codeBox": _html_code, "image": _html_image}.get(type_)
    if rendu is None:
        return _html_marqueur(type_, data)
    return rendu(data)


def _html_titre(data: dict) -> str:
    niveau = data.get("level") if data.get("level") in TITRES.values() else 2
    return f"<h{niveau}>{data.get('text', '')}</h{niveau}>"


def _html_paragraphe(data: dict) -> str:
    return f"<p>{data.get('text', '')}</p>"


def _html_liste(data: dict) -> str:
    balise = "ol" if data.get("style") == "ordered" else "ul"
    return f"<{balise}>{_html_items(data.get('items') or [])}</{balise}>"


def _html_items(items, balise: str = "ul") -> str:
    morceaux = []
    for item in items:
        if not isinstance(item, dict):
            continue
        enfants = item.get("items") or []
        dedans = f"<{balise}>{_html_items(enfants, balise)}</{balise}>" if enfants else ""
        morceaux.append(f"<li>{item.get('content', '')}{dedans}</li>")
    return "".join(morceaux)


def _html_tableau(data: dict) -> str:
    lignes = [l for l in (data.get("content") or []) if isinstance(l, list)]
    if not lignes:
        return ""
    corps = lignes
    entete = ""
    if data.get("withHeadings"):
        entete = "<thead><tr>" + "".join(f"<th>{c}</th>" for c in lignes[0]) + "</tr></thead>"
        corps = lignes[1:]
    cellules = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in ligne) + "</tr>" for ligne in corps)
    return f"<table>{entete}<tbody>{cellules}</tbody></table>"


def _html_code(data: dict) -> str:
    langage = data.get("language") if data.get("language") in LANGAGES else "text"
    return f'<pre data-langage="{langage}"><code>{data.get("code", "")}</code></pre>'


def _html_image(data: dict) -> str:
    url = data.get("url", "")
    if not _MEDIA.fullmatch(url):
        return ""
    return (f'<figure><img src="{url}">'
            f'<figcaption>{data.get("caption", "")}</figcaption></figure>')


def _html_marqueur(type_: str, data: dict) -> str:
    """Repère non rédactionnel : un exercice cité par son identifiant, ou tout autre bloc, porté en JSON."""
    if not isinstance(type_, str) or not _TYPE_DE_BLOC.fullmatch(type_):
        return ""
    libelle = _MARQUEURS.get(type_)
    valeur = data.get(type_)
    if libelle and isinstance(valeur, str) and valeur:
        return (f'<p data-bloc="{type_}" data-cle="{type_}" data-valeur="{html.escape(valeur)}">'
                f'{libelle} : {_e(valeur)}</p>')
    return f'<p data-bloc="{type_}" data-json="{html.escape(json.dumps(data, ensure_ascii=False))}">Bloc {type_}</p>'


# --- HTML vers blocs ---------------------------------------------------------------------------------------------

def vers_blocs(code_html: str) -> list[dict]:
    """Blocs EditorJS relus depuis le HTML enregistré par l'éditeur riche. Tout ce qui n'est pas attendu tombe."""
    lecteur = _Lecteur()
    lecteur.feed(code_html or "")
    lecteur.close()
    return lecteur.terminer()


def _bloc(type_: str, **data) -> dict:
    return {"type": type_, "data": data}


class _Lecteur(HTMLParser):
    """Lit le HTML du formulaire et n'en garde que ce qu'une rubrique peut contenir."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocs: list[dict] = []
        self._ignore: str | None = None  # balise dont tout le contenu est écarté (script, repère)
        self._texte: list[str] | None = None  # collecte de texte en cours
        self._titre_niveau: int | None = None
        self._listes: list[dict] = []
        self._tableau: dict | None = None
        self._ligne: list[str] | None = None
        self._code: str | None = None
        self._image: dict | None = None
        self._inline: list[str] = []  # balises de mise en forme ouvertes et retenues
        self._libre: list[str] = []  # texte nu, hors de toute balise de bloc

    # -- utilitaires
    def _collecter(self) -> None:
        self._texte = []

    def _recolte(self) -> str:
        texte = "".join(self._texte or []).strip()
        self._texte = None
        self._inline = []
        return texte

    def _poser_libre(self) -> None:
        texte = "".join(self._libre).strip()
        self._libre = []
        if texte:
            self.blocs.append(_bloc("paragraph", text=texte))

    def _poser_image(self) -> None:
        if self._image is not None:
            self.blocs.append(_bloc("image", url=self._image["url"], caption=self._image["caption"],
                                    withBorder=False, withBackground=False, stretched=False))
            self._image = None

    def _nouveau_bloc(self) -> None:
        """Un bloc commence : ce qui traînait en texte nu ou en image devient un bloc à son tour."""
        self._poser_libre()
        self._poser_image()

    # -- lecture
    def handle_starttag(self, tag, attrs):
        if self._ignore:
            return
        a = {nom: (valeur or "") for nom, valeur in attrs}
        if tag in ("script", "style", "iframe", "object", "embed"):
            self._ignore = tag
            return
        if tag in INLINE and self._texte is not None:
            if self._code is not None:  # dans un bloc de code, tout est du texte
                return
            ouverture = self._ouvrir_inline(tag, a)
            if ouverture:
                self._texte.append(ouverture)
            if tag != "br":
                self._inline.append(tag if ouverture else "")
            return
        self._bloc_ouvre(tag, a)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ("br", "img"):
            self.handle_endtag(tag)

    def _ouvrir_inline(self, tag: str, a: dict) -> str:
        if tag == "br":
            return "<br>"
        if tag == "a":
            lien = a.get("href", "")
            return f'<a href="{html.escape(lien)}">' if _LIEN.fullmatch(lien) else ""
        return f"<{tag}>"

    def _bloc_ouvre(self, tag: str, a: dict) -> None:
        if tag in TITRES:
            self._nouveau_bloc()
            self._titre_niveau = TITRES[tag]
            self._collecter()
        elif tag == "p":
            self._nouveau_bloc()
            if "data-bloc" in a:
                self._marqueur(a)
                self._ignore = "p"
            else:
                self._collecter()
        elif tag in ("ul", "ol"):
            if not self._listes:
                self._nouveau_bloc()
            self._listes.append({"style": "ordered" if tag == "ol" else "unordered", "items": []})
        elif tag == "li":
            self._collecter()
        elif tag == "table":
            self._nouveau_bloc()
            self._tableau = {"withHeadings": False, "content": []}
        elif tag == "tr":
            self._ligne = []
        elif tag in ("th", "td"):
            if tag == "th" and self._tableau is not None:
                self._tableau["withHeadings"] = True
            self._collecter()
        elif tag == "pre":
            self._nouveau_bloc()
            self._code = a.get("data-langage", "text")
            self._collecter()
        elif tag == "img":
            self._nouveau_bloc()
            source = a.get("src", "")
            if _MEDIA.fullmatch(source):
                self._image = {"url": source, "caption": ""}
        elif tag == "figcaption":
            if self._image is not None:
                self._collecter()
        elif tag == "figure":
            self._nouveau_bloc()

    def handle_endtag(self, tag):
        if self._ignore:
            if self._ignore == tag:
                self._ignore = None
            return
        if tag in INLINE and self._texte is not None:
            if tag == "br" or self._code is not None:
                return
            if self._inline and self._inline[-1] == tag:
                self._texte.append(f"</{tag}>")
            if self._inline:
                self._inline.pop()
            return
        self._bloc_ferme(tag)

    def _bloc_ferme(self, tag: str) -> None:
        if tag in TITRES and self._titre_niveau is not None:
            texte = self._recolte()
            if texte:
                self.blocs.append(_bloc("header", text=texte, level=self._titre_niveau))
            self._titre_niveau = None
        elif tag == "p" and self._texte is not None:
            texte = self._recolte()
            if texte:
                self.blocs.append(_bloc("paragraph", text=texte))
        elif tag == "li" and self._listes:
            contenu = self._recolte()
            if contenu:
                self._listes[-1]["items"].append({"content": contenu, "items": []})
        elif tag in ("ul", "ol") and self._listes:
            liste = self._listes.pop()
            if not liste["items"]:
                return
            if self._listes and self._listes[-1]["items"]:
                self._listes[-1]["items"][-1]["items"] = liste["items"]
            elif not self._listes:
                self.blocs.append(_bloc("list", style=liste["style"], items=liste["items"]))
        elif tag in ("th", "td") and self._ligne is not None:
            self._ligne.append(self._recolte())
        elif tag == "tr" and self._tableau is not None and self._ligne:
            self._tableau["content"].append(self._ligne)
            self._ligne = None
        elif tag == "table" and self._tableau is not None:
            if self._tableau["content"]:
                self.blocs.append(_bloc("table", withHeadings=self._tableau["withHeadings"],
                                        content=self._tableau["content"]))
            self._tableau = None
        elif tag == "pre" and self._code is not None:
            code = "".join(self._texte or []).strip("\n")
            self._texte = None
            langage = self._code if self._code in LANGAGES else "text"
            self._code = None
            if code.strip():
                self.blocs.append(_bloc("codeBox", code=code, language=langage))
        elif tag == "figcaption" and self._image is not None:
            self._image["caption"] = self._recolte()
        elif tag == "figure":
            self._poser_image()

    def _marqueur(self, a: dict) -> None:
        type_ = a.get("data-bloc", "")
        if not _TYPE_DE_BLOC.fullmatch(type_):
            return
        if "data-json" in a:
            try:
                data = json.loads(a["data-json"])
            except ValueError:
                return
            if isinstance(data, dict) and all(isinstance(c, str) for c in data):
                self.blocs.append({"type": type_, "data": data})
            return
        cle, valeur = a.get("data-cle", ""), a.get("data-valeur", "")
        if _CLE.fullmatch(cle) and valeur:
            self.blocs.append({"type": type_, "data": {cle: valeur}})

    def handle_data(self, donnees):
        if self._ignore:
            return
        if self._texte is not None:
            self._texte.append(_e(donnees))
        else:
            self._libre.append(_e(donnees))

    def terminer(self) -> list[dict]:
        """Ferme ce qui restait ouvert : un éditeur rend parfois du HTML non refermé."""
        if self._texte is not None:
            texte = self._recolte()
            if texte:
                self.blocs.append(_bloc("paragraph", text=texte))
        self._poser_image()
        self._poser_libre()
        return self.blocs
