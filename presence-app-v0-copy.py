import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
import re

# Configuration de la page Streamlit
st.set_page_config(page_title="Liste de Présence au Culte", layout="wide")

# Ajouter le titre à gauche et le logo à droite
col1, col2 = st.columns([3, 1])  # La colonne de gauche est 3 fois plus large que celle de droite
with col1:
    st.title("📌 Liste de Présence au Culte")  # Titre aligné à gauche
with col2:
    st.image("assets/EDC_logo_white.jpg", width=100, use_column_width=False)  # Logo à droite, taille fixe

st.write("")
st.write("")
st.markdown("<div style='text-align: left; font-size: 24px; font-weight: normal;'>Bienvenue au culte à l'église Édifice Du Christ</div>", unsafe_allow_html=True)
st.write("")
st.write("Veuillez entrer vos informations de contact")
st.write("")

# Connexion à Supabase via l'API
supabase_url = st.secrets["supabase"]["url"]  
supabase_key = st.secrets["supabase"]["key"]  
supabase: Client = create_client(supabase_url, supabase_key)

# Génération de l'ID membre sous la forme MEMBERXXXXX
def generate_member_id():
    try:
        response = supabase.table("dim_membres").select("member_id", count="exact").execute()
        count = response.count + 1
        return f"MEMBER{count:06d}"
    except Exception as e:
        st.error(f"Erreur lors de la génération de l'ID: {e}")
        return "MEMBER000001"

# Fonction de validation d'email
def is_valid_email(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email)) if email else True

# Fonction de validation de numéro de téléphone
def is_valid_phone(phone):
    cleaned_phone = re.sub(r'[\s\-().]+', '', phone)
    phone_pattern = r'^(\+?\d{8,15})$'
    return bool(re.match(phone_pattern, cleaned_phone))

# Fonction pour formater le numéro de téléphone
def format_phone_number(phone):
    cleaned_phone = re.sub(r'[\s\-().]+', '', phone)
    if not cleaned_phone.startswith('+'):
        if len(cleaned_phone) == 10:
            cleaned_phone = "+225" + cleaned_phone
        else:
            cleaned_phone = "+" + cleaned_phone
    return cleaned_phone

# Fonction pour réinitialiser le formulaire
def reset_form():
    st.session_state.validation_errors = {}
    st.session_state.show_success = False
    st.session_state.show_warning = False
    st.session_state.form_submitted = False
    st.session_state.form_key = f"presence_form_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    st.rerun()

# Initialisation des variables de session
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False
if "show_success" not in st.session_state:
    st.session_state.show_success = False
if "show_warning" not in st.session_state:
    st.session_state.show_warning = False
if "validation_errors" not in st.session_state:
    st.session_state.validation_errors = {}
if "form_key" not in st.session_state:
    st.session_state.form_key = "presence_form"

# Formulaire
with st.form(key=st.session_state.form_key, clear_on_submit=False):
    nom = st.text_input("Nom")
    prenoms = st.text_input("Prénoms")
    sexe = st.selectbox("Sexe", ["Masculin", "Féminin"], index=0)
    date_naissance = st.date_input(
        "Date de naissance",
        value=date(2000, 1, 1),
        min_value=date(1900, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY"
    )
    contact = st.text_input("Contact", help="Ex: 0102030405 ou +22501020304")
    email = st.text_input("Email", help="Ex: nom@domaine.com (optionnel)")
    lieu_habitation = st.text_input("Lieu d'habitation")
    
    col_question = st.container()
    col_question.markdown("<span>Assistez-vous au culte pour la première fois ?</span>", unsafe_allow_html=True)
    first_time = col_question.radio("", ["Oui", "Non"], horizontal=True, label_visibility="collapsed")
    
    col1, col2 = st.columns(2)
    with col1:
        submit_button = st.form_submit_button("Confirmer présence")
    with col2:
        reset_button = st.form_submit_button("Réinitialiser", type="secondary")

# Conteneur pour tous les messages en bas du formulaire
message_placeholder = st.container()

# Réinitialisation
if reset_button:
    reset_form()

# Soumission
if submit_button:
    # Réinitialiser les messages et erreurs dès le clic sur "Confirmer présence"
    st.session_state.validation_errors = {}
    st.session_state.show_success = False
    st.session_state.show_warning = False
    
    # Validation des champs
    input_valid = True
    
    if not nom.strip():
        st.session_state.validation_errors["nom"] = "Le nom est obligatoire"
        input_valid = False
    if not prenoms.strip():
        st.session_state.validation_errors["prenoms"] = "Les prénoms sont obligatoires"
        input_valid = False
    if not sexe:
        st.session_state.validation_errors["sexe"] = "Le sexe est obligatoire"
        input_valid = False
    if not date_naissance:
        st.session_state.validation_errors["date_naissance"] = "La date de naissance est obligatoire"
        input_valid = False
    elif (date.today() - date_naissance).days // 365 > 120:
        st.session_state.validation_errors["date_naissance"] = "Date de naissance incorrecte"
        input_valid = False
    if not contact.strip():
        st.session_state.validation_errors["contact"] = "Le contact est obligatoire"
        input_valid = False
    elif not is_valid_phone(contact.strip()):
        st.session_state.validation_errors["contact"] = "Format de numéro invalide"
        input_valid = False
    email_lower = email.strip().lower()
    if email_lower and not is_valid_email(email_lower):
        st.session_state.validation_errors["email"] = "Format d'email invalide"
        input_valid = False
    if not lieu_habitation.strip():
        st.session_state.validation_errors["lieu_habitation"] = "Le lieu d'habitation est obligatoire"
        input_valid = False
    
    # Si tout est valide, procéder à l'enregistrement
    if input_valid:
        nom_formate = nom.strip().upper()
        prenoms_formate = prenoms.strip().title()
        contact_formate = format_phone_number(contact.strip())
        email_formate = email_lower if email_lower else None
        lieu_habitation_formate = lieu_habitation.strip().title()
        
        try:
            # Vérifier si le membre existe déjà
            response = supabase.table("dim_membres").select("member_id", "date_de_premier_culte").eq("nom", nom_formate).eq("prenoms", prenoms_formate).execute()
            
            if response.data:  # Si le membre existe
                member_id = response.data[0]["member_id"]
                date_premier_culte = response.data[0]["date_de_premier_culte"]
                est_nouveau = first_time == "Oui"
                
                update_data = {}
                if contact_formate:
                    update_data["contact"] = contact_formate
                if email_formate:
                    update_data["email"] = email_formate
                if lieu_habitation_formate:
                    update_data["lieu_d_habitation"] = lieu_habitation_formate
                
                if update_data:
                    supabase.table("dim_membres").update(update_data).eq("member_id", member_id).execute()
            else:  # Nouveau membre
                member_id = generate_member_id()
                est_nouveau = True
                date_premier_culte = date.today().isoformat() if first_time == "Oui" else None
                
                supabase.table("dim_membres").insert({
                    "member_id": member_id,
                    "nom": nom_formate,
                    "prenoms": prenoms_formate,
                    "sexe": sexe,
                    "date_de_naissance": date_naissance.isoformat(),
                    "contact": contact_formate,
                    "email": email_formate,
                    "lieu_d_habitation": lieu_habitation_formate,
                    "date_de_premier_culte": date_premier_culte
                }).execute()

            # Vérifier si la présence est déjà enregistrée aujourd'hui
            today_str = date.today().isoformat()
            presence_response = supabase.table("fact_presence_au_culte").select("member_id", count="exact").eq("member_id", member_id).eq("date", today_str).execute()
            
            if presence_response.count == 0:  # Pas encore présent aujourd'hui
                supabase.table("fact_presence_au_culte").insert({
                    "member_id": member_id,
                    "nom": nom_formate,
                    "prenoms": prenoms_formate,
                    "date": today_str,
                    "est_nouveau": first_time == "Oui",
                    "est_present": True
                }).execute()
                
                st.session_state.show_success = True
                st.session_state.form_submitted = True
            else:
                st.session_state.show_warning = True
                
        except Exception as e:
            with message_placeholder:
                # Vérifier si c'est une erreur de doublon (code PostgreSQL 23505)
                if hasattr(e, 'code') and e.code == '23505' and 'contact' in str(e):
                    st.error("Erreur : Ce numéro de téléphone existe déjà, veuillez en mettre un autre")
                else:
                    st.error(f"Erreur lors de l'enregistrement: {e}")

# Afficher les messages dans le conteneur après soumission
if st.session_state.validation_errors:
    with message_placeholder:
        for error_msg in st.session_state.validation_errors.values():
            st.error(f"Erreur : {error_msg}")

if st.session_state.show_success:
    with message_placeholder:
        st.success("✅ Présence confirmée et membre enregistré !")

if st.session_state.show_warning:
    with message_placeholder:
        st.warning("⚠️ Ce membre est déjà enregistré pour aujourd'hui !")