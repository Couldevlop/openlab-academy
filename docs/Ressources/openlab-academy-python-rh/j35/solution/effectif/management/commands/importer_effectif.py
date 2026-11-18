"""La commande d'import : elle réutilise le cœur, elle ne le réécrit pas."""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from effectif.models import Poste, Salarie

COLONNES = ("matricule", "nom", "poste", "date_embauche", "salaire_fcfa")


class Command(BaseCommand):
    """Importe un effectif depuis un fichier CSV, sans créer de doublon."""

    help = "Importe un effectif depuis un fichier CSV."

    def add_arguments(self, parseur):
        """Déclare le seul argument : le chemin du fichier."""
        parseur.add_argument("fichier", help="chemin du fichier CSV à importer")

    def handle(self, *args, **options):
        """Lit le fichier et écrit les salariés absents de la base."""
        chemin = Path(options["fichier"])
        if not chemin.is_file():
            raise CommandError(f"Fichier introuvable : {chemin}")
        with chemin.open(encoding="utf-8", newline="") as fichier:
            lignes = list(csv.DictReader(fichier))
        manquantes = [colonne for colonne in COLONNES
                      if lignes and colonne not in lignes[0]]
        if manquantes:
            raise CommandError(f"Colonnes absentes : {', '.join(manquantes)}")
        crees, ignores = 0, 0
        with transaction.atomic():
            for numero, ligne in enumerate(lignes, start=2):
                if self._ecrire(ligne, numero):
                    crees += 1
                else:
                    ignores += 1
        self.stdout.write(f"{crees} salarié(s) créé(s), {ignores} ignoré(s).")

    def _ecrire(self, ligne, numero):
        """Crée un salarié, ou rend False si son matricule est déjà en base."""
        matricule = ligne["matricule"].strip().upper()
        if Salarie.objects.filter(matricule=matricule).exists():
            return False
        try:
            salaire = int(ligne["salaire_fcfa"])
        except ValueError as erreur:
            raise CommandError(f"Salaire illisible ligne {numero} : "
                               f"{ligne['salaire_fcfa']!r}") from erreur
        poste, _ = Poste.objects.get_or_create(libelle=ligne["poste"].strip())
        Salarie.objects.create(matricule=matricule, nom=ligne["nom"].strip(), poste=poste,
                               date_embauche=ligne["date_embauche"], salaire_fcfa=salaire)
        return True
