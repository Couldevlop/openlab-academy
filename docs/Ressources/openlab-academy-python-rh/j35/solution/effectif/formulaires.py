"""Les formulaires : la frontière où les données saisies deviennent acceptables.

La validation vit ici, côté serveur. Ce qui est vérifié dans le navigateur est un confort pour
l'utilisateur, jamais une garantie : une requête peut arriver sans passer par la page.
"""
from datetime import date

from django import forms

from effectif.models import Salarie


class EmbaucheForm(forms.ModelForm):
    """Le formulaire d'embauche d'un salarié."""

    class Meta:
        model = Salarie
        fields = ("matricule", "nom", "poste", "date_embauche", "salaire_fcfa")

    def clean_matricule(self):
        """Normalise le matricule et refuse un doublon, quelle que soit la casse saisie."""
        matricule = self.cleaned_data["matricule"].strip().upper()
        if Salarie.objects.filter(matricule__iexact=matricule).exists():
            raise forms.ValidationError("Ce matricule est déjà attribué.")
        return matricule

    def clean_date_embauche(self):
        """Refuse une embauche postérieure à aujourd'hui."""
        valeur = self.cleaned_data["date_embauche"]
        if valeur > date.today():
            raise forms.ValidationError("La date d'embauche ne peut pas être dans le futur.")
        return valeur
