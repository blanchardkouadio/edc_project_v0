import streamlit as st

# Initialisation des variables de session
if "init" not in st.session_state:
    st.session_state.init = True
    st.session_state.validation_errors = {}  # Stocke les erreurs
    st.session_state.show_success = False    # Message de succès
    st.session_state.display_messages = False  # Drapeau pour afficher les messages
    st.session_state.form_key = "form_initial"  # Clé unique pour le formulaire

# Fonction de réinitialisation
def request_reset():
    st.session_state.validation_errors = {}
    st.session_state.show_success = False
    st.session_state.display_messages = False  # Désactiver l’affichage avant relance
    st.session_state.form_key = f"form_{st.session_state.form_key}_reset"
    st.rerun()  # Relancer l’application

# Formulaire
with st.form(key=st.session_state.form_key):
    nom = st.text_input("Nom")
    submit_button = st.form_submit_button("Confirmer")

# Conteneur pour les messages
message_container = st.container()

# Traitement du formulaire
if submit_button:
    st.session_state.validation_errors = {}  # Réinitialiser les erreurs
    st.session_state.show_success = False
    st.session_state.display_messages = True  # Activer l’affichage des messages

    # Validation simple
    if not nom.strip():
        st.session_state.validation_errors["nom"] = "Le nom est obligatoire"
    else:
        st.session_state.show_success = True

# Affichage des messages uniquement si display_messages est True
if st.session_state.display_messages:
    with message_container:
        if st.session_state.validation_errors:
            for error_msg in st.session_state.validation_errors.values():
                st.error(f"Erreur : {error_msg}")
            if st.button("Corriger les erreurs"):
                request_reset()  # Réinitialiser et relancer

        if st.session_state.show_success:
            st.success("✅ Succès !")
            if st.button("Nouvelle saisie"):
                request_reset()  # Réinitialiser et relancer
