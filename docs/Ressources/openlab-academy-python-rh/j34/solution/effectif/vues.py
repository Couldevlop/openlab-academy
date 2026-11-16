"""Les vues : elles répondent, et délèguent le calcul."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from effectif.formulaires import EmbaucheForm
from effectif.models import Salarie
from effectif.roles import voit_les_salaires
from effectif.requetes import masse_salariale_par_poste


@login_required
def liste_salaries(requete):
    """Affiche la liste des salariés, leur poste chargé avec eux."""
    salaries = Salarie.objects.select_related("poste").all()
    autorise = voit_les_salaires(requete.user)
    return render(requete, "effectif/liste.html",
                  {"salaries": salaries,
                   "etat": masse_salariale_par_poste() if autorise else {},
                   "voit_les_salaires": autorise})


@login_required
def fiche_salarie(requete, matricule):
    """Affiche la fiche d'un salarié, ou rend 404 s'il n'existe pas."""
    salarie = get_object_or_404(Salarie.objects.select_related("poste"), matricule=matricule)
    autorise = voit_les_salaires(requete.user)
    fiche = {"matricule": salarie.matricule, "nom": salarie.nom,
             "poste": salarie.poste.libelle, "date_embauche": salarie.date_embauche}
    if autorise:
        fiche["salaire_fcfa"] = salarie.salaire_fcfa
    return render(requete, "effectif/fiche.html",
                  {"salarie": fiche, "voit_les_salaires": autorise})


@login_required
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
