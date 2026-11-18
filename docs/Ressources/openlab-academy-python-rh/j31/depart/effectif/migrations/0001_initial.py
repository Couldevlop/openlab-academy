"""Première migration de l'effectif : les trois modèles et leurs contraintes."""
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Crée Poste, Salarie et Absence."""

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Poste",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                           verbose_name="ID")),
                ("libelle", models.CharField(max_length=60, unique=True,
                                             verbose_name="libellé")),
            ],
            options={"verbose_name": "poste", "ordering": ("libelle",)},
        ),
        migrations.CreateModel(
            name="Salarie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                           verbose_name="ID")),
                ("matricule", models.CharField(max_length=16, unique=True)),
                ("nom", models.CharField(max_length=120)),
                ("date_embauche", models.DateField(verbose_name="date d'embauche")),
                ("salaire_fcfa", models.PositiveIntegerField(
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name="salaire (FCFA)")),
                ("poste", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                            related_name="salaries", to="effectif.poste")),
            ],
            options={"verbose_name": "salarié", "verbose_name_plural": "salariés",
                     "ordering": ("matricule",)},
        ),
        migrations.CreateModel(
            name="Absence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                           verbose_name="ID")),
                ("date_debut", models.DateField(verbose_name="début")),
                ("date_fin", models.DateField(verbose_name="fin")),
                ("motif", models.CharField(blank=True, max_length=120)),
                ("salarie", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="absences", to="effectif.salarie")),
            ],
            options={"verbose_name": "absence", "ordering": ("-date_debut",)},
        ),
        migrations.AddConstraint(
            model_name="absence",
            constraint=models.CheckConstraint(
                condition=models.Q(date_fin__gte=models.F("date_debut")),
                name="absence_fin_apres_debut"),
        ),
    ]
