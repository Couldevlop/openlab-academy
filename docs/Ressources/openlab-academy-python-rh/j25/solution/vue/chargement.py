"""Le chargement de l'effectif pour l'écran, mis en cache une fois pour toutes."""
import streamlit as st

from rh.exemple import FICHES


@st.cache_data
def charger_effectif():
    """Rend l'effectif affiché par l'écran, relu seulement quand le cache est vidé."""
    return list(FICHES)
