"""Les modèles de l'effectif : la forme des données, et leurs garde-fous en base."""
from django.core.validators import MinValueValidator
from django.db import models


class Poste(models.Model):
    """Un intitulé de poste, partagé par plusieurs salariés."""

    libelle = models.CharField("libellé", max_length=60, unique=True)

    class Meta:
        verbose_name = "poste"
        ordering = ("libelle",)

    def __str__(self):
        return self.libelle


class Salarie(models.Model):
    """Un salarié de l'entreprise."""

    matricule = models.CharField(max_length=16, unique=True)
    nom = models.CharField(max_length=120)
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT, related_name="salaries")
    date_embauche = models.DateField("date d'embauche")
    salaire_fcfa = models.PositiveIntegerField("salaire (FCFA)",
                                               validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "salarié"
        verbose_name_plural = "salariés"
        ordering = ("matricule",)

    def __str__(self):
        return f"{self.matricule} {self.nom}"


class Absence(models.Model):
    """Une absence posée sur une période."""

    salarie = models.ForeignKey(Salarie, on_delete=models.CASCADE, related_name="absences")
    date_debut = models.DateField("début")
    date_fin = models.DateField("fin")
    motif = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "absence"
        ordering = ("-date_debut",)
        constraints = [
            models.CheckConstraint(condition=models.Q(date_fin__gte=models.F("date_debut")),
                                   name="absence_fin_apres_debut"),
        ]

    def __str__(self):
        return f"{self.salarie.matricule} du {self.date_debut} au {self.date_fin}"
