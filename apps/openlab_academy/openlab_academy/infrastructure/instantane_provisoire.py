"""Adaptateur provisoire du port Instantane : garde le lien tel quel, sans lire le dépôt (remplacé par l'adaptateur réel)."""


class InstantaneProvisoire:
    def prendre(self, url: str) -> tuple[str, str]:
        return url, ""
