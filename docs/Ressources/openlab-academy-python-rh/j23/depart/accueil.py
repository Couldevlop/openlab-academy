"""L'écran RH : il affiche, il ne calcule pas."""
import streamlit as st

from rh.exemple import FICHES
from vue.donnees import colonnes_affichees, filtrer, postes

st.set_page_config(page_title="Effectif RH", layout="centered")
st.title("Effectif RH")
st.caption("Données de démonstration, entièrement fictives.")

choix = st.sidebar.selectbox("Poste", ["Tous les postes", *postes(FICHES)])
minimum = st.sidebar.number_input("Salaire minimum (FCFA)", min_value=0, step=10000, value=0)
poste = None if choix == "Tous les postes" else choix

retenues = filtrer(FICHES, poste=poste, salaire_minimum=minimum)
st.write(f"{len(retenues)} salarié(s) retenu(s).")
st.dataframe(colonnes_affichees(retenues), use_container_width=True)

# À écrire : la ligne de trois indicateurs de l'énoncé.
