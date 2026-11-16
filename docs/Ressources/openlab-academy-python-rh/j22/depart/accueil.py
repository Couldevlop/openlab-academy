"""L'écran RH : il affiche, il ne calcule pas."""
import streamlit as st

from rh.exemple import FICHES
from vue.donnees import colonnes_affichees

st.set_page_config(page_title="Effectif RH", layout="centered")
st.title("Effectif RH")
st.caption("Données de démonstration, entièrement fictives.")
st.dataframe(colonnes_affichees(FICHES), use_container_width=True)

# À écrire : les deux filtres de la barre latérale, et le tableau filtré.
