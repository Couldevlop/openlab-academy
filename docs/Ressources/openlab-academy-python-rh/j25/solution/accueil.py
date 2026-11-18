"""L'écran RH : il affiche, il ne calcule pas."""
import streamlit as st

from vue.chargement import charger_effectif
from rh.calculs import formater_fcfa
from rh.indicateurs import effectif_total, masse_salariale, salaire_median
from vue.donnees import colonnes_affichees, filtrer, postes
from vue.graphiques import libelle_axe, serie_masse_par_poste

st.set_page_config(page_title="Effectif RH", layout="centered")

FICHES = charger_effectif()
st.title("Effectif RH")
st.caption("Données de démonstration, entièrement fictives.")

choix = st.sidebar.selectbox("Poste", ["Tous les postes", *postes(FICHES)])
minimum = st.sidebar.number_input("Salaire minimum (FCFA)", min_value=0, step=10000, value=0)
poste = None if choix == "Tous les postes" else choix

retenues = filtrer(FICHES, poste=poste, salaire_minimum=minimum)

premier, deuxieme, troisieme = st.columns(3)
premier.metric("Effectif", effectif_total(retenues))
deuxieme.metric("Masse salariale", formater_fcfa(masse_salariale(retenues)))
troisieme.metric("Salaire médian", formater_fcfa(salaire_median(retenues)))
st.dataframe(colonnes_affichees(retenues), use_container_width=True)

serie = serie_masse_par_poste(retenues)
if serie:
    st.subheader(f"Masse salariale par poste, en {libelle_axe(max(serie.values()))}")
    st.bar_chart(serie)
else:
    st.info("Aucun salarié ne correspond aux filtres choisis.")
