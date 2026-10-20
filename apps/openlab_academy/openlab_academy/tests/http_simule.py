"""Réponses HTTP simulées : les tests ne sortent jamais sur le réseau."""
import json as json_


class Reponse:
    def __init__(self, statut=200, json=None, texte="", octets=None):
        self.status_code = statut
        self._json = json
        if octets is None:
            octets = json_.dumps(json).encode("utf-8") if json is not None else texte.encode("utf-8")
        self._octets = octets
        self.fermee = False

    def json(self):
        if self._json is None:
            return json_.loads(self._octets.decode("utf-8"))
        return self._json

    def iter_content(self, taille):
        for i in range(0, len(self._octets), taille):
            yield self._octets[i:i + taille]

    def close(self):
        self.fermee = True


SHA = "a" * 40


def github(routes: dict | None = None, prive=False, arbre=None, fichiers=None):
    """Simule l'API publique GitHub pour le dépôt aya/livrable ; `routes` remplace une réponse par chemin."""
    arbre = arbre if arbre is not None else ["README.md", "src/app.py", "tests/test_app.py"]
    fichiers = fichiers if fichiers is not None else {"README.md": "# Livrable\nInstallation : make", "src/app.py": "print(1)",
                                                      "tests/test_app.py": "def test(): pass"}
    base = "https://api.github.com/repos/aya/livrable"
    table = {
        base: Reponse(json={"private": prive, "default_branch": "main"}),
        f"{base}/commits/main": Reponse(json={"sha": SHA}),
        f"{base}/git/trees/{SHA}": Reponse(json={"tree": [{"path": p, "type": "blob", "size": 10} for p in arbre]
                                                 + [{"path": "src", "type": "tree"}]}),
    }
    for chemin, texte in fichiers.items():
        table[f"{base}/contents/{chemin}"] = Reponse(texte=texte)
    table.update(routes or {})

    def get(url, **_):
        reponse = table.get(url, Reponse(404))
        if isinstance(reponse, Exception):
            raise reponse
        return reponse
    return get
