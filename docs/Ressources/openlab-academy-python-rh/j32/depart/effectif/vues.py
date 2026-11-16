"""Les vues : elles répondent, et délèguent le calcul."""
from django.shortcuts import get_object_or_404, redirect, render

from effectif.formulaires import EmbaucheForm
from effectif.models import Salarie
from effectif.requetes import masse_salariale_par_poste


def liste_salaries(requete):
    """Affiche la liste des salariés, leur poste chargé avec eux."""
    salaries = Salarie.objects.select_related("poste").all()
    return render(requete, "effectif/liste.html",
                  {"salaries": salaries, "etat": masse_salariale_par_poste()})


def fiche_salarie(requete, matricule):
    """Affiche la fiche d'un salarié, ou rend 404 s'il n'existe pas."""
    salarie = get_object_or_404(Salarie.objects.select_related("poste"), matricule=matricule)
    return render(requete, "effectif/fiche.html", {"salarie": salarie})


def embaucher(requete):
    """Affiche le formulaire d'embauche, et n'enregistre que ce qui est valide."""
    if requete.method == "POST":
        formulaire = EmbaucheForm(requete.POST)
        if formulaire.is_valid():
            salarie = formulaire.save()
            return redirect("fiche-salarie", matricule=salarie.matricule)
    else:
        formulaire = EmbaucheForm()
    return render(requete, "effectif/embauche.html", {"formulaire": formulaire})
