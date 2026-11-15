import frappe
from frappe.model.document import Document

from openlab_academy.infrastructure import retouches_frappe

# champs qu'une publication seule écrit : l'identité de la partie et les blocs venus du fichier de parcours
FIGES = ("lecon", "cle", "rang", "blocs")


class PartieLeconOpenLab(Document):
    def validate(self):
        """Hors publication, une partie ne se modifie que par son texte et son titre.

        `blocs` sert tel quel à assembler la leçon tant que la partie n'est pas retouchée : un bloc écrit à la
        main y passerait sans la liste blanche de `html_blocs`, donc sans échappement (OWASP A03). La case
        « lecture seule » du formulaire ne protège que l'écran ; l'API, elle, écrit ce qu'on lui donne. Ces
        champs reviennent donc à leur valeur en base, quel que soit le chemin d'écriture."""
        if self.is_new() or frappe.flags.get(retouches_frappe.DRAPEAU):
            return
        avant = self.get_doc_before_save()
        if avant is None:
            return
        for champ in FIGES:
            if self.get(champ) != avant.get(champ):
                self.set(champ, avant.get(champ))
