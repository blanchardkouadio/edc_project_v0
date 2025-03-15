import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
import re

# Initialisation des variables d'état
if "init" not in st.session_state:
    st.session_state.init = True
    st.session_state.validation_errors = {}
    st.session_state.show_success = False
    st.session_state.show_warning = False
    st.session_state.form_submitted = False
    st.session_state.reset_requested = False
    st.session_state.form_key = "presence_form_initial"
    st.session_state.page = "attendance"  # Page par défaut
    st.session_state.visitor_checkboxes = {}  # Pour stocker l'état des cases à cocher

# Fonction pour réinitialiser l'état
def reset_state():
    st.session_state.validation_errors = {}
    st.session_state.show_success = False
    st.session_state.show_warning = False
    st.session_state.form_submitted = False
    st.session_state.form_key = f"presence_form_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

# Gérer la réinitialisation au début du script
if st.session_state.reset_requested:
    reset_state()
    st.session_state.reset_requested = False
    st.rerun()

# Configuration de la page
st.set_page_config(page_title="Église Édifice Du Christ", layout="wide")

# Connexion à Supabase
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["key"]
supabase: Client = create_client(supabase_url, supabase_key)

# Fonction pour générer un ID temporaire (TEMP00X)
def generate_temp_id():
    try:
        # Récupérer tous les member_id
        response = supabase.table("dim_membres").select("member_id").execute()
        # Filtrer les ID commençant par TEMP côté client
        temp_ids = [entry['member_id'] for entry in response.data if entry['member_id'].startswith('TEMP')]
        count = len(temp_ids) + 1
        return f"TEMP{count:03d}"  # Exemple : TEMP001, TEMP002, etc.
    except Exception as e:
        st.error(f"Erreur lors de la génération de l'ID temporaire: {e}")
        return "TEMP001"  # Valeur par défaut en cas d'erreur

# Fonction pour générer un ID membre (MEMBER0000X)
def generate_member_id():
    try:
        # Récupérer tous les member_id
        response = supabase.table("dim_membres").select("member_id").execute()
        # Filtrer les ID commençant par MEMBER côté client
        member_ids = [entry['member_id'] for entry in response.data if entry['member_id'].startswith('MEMBER')]
        count = len(member_ids) + 1
        return f"MEMBER{count:05d}"  # Format avec 5 chiffres, ex: MEMBER00001
    except Exception as e:
        st.error(f"Erreur lors de la génération de l'ID membre: {e}")
        return "MEMBER00001"  # Valeur par défaut en cas d'erreur

# Validation de l'email
def is_valid_email(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email)) if email else True

# Validation et formatage du numéro de téléphone
def is_valid_phone(phone):
    cleaned_phone = re.sub(r'[\s\-().]+', '', phone)
    phone_pattern = r'^(\+?\d{8,15})$'
    return bool(re.match(phone_pattern, cleaned_phone))

def format_phone_number(phone):
    cleaned_phone = re.sub(r'[\s\-().]+', '', phone)
    if not cleaned_phone.startswith('+'):
        if len(cleaned_phone) == 10:
            cleaned_phone = "+225" + cleaned_phone
        else:
            cleaned_phone = "+" + cleaned_phone
    return cleaned_phone

# Fonction pour convertir un invité en membre
def convert_visitor_to_member(member_id):
    try:
        # Générer un nouvel ID de membre
        new_member_id = generate_member_id()
        
        # 1. Créer une copie temporaire des données de présence
        presence_data = supabase.table("fact_presence_au_culte").select("*").eq("member_id", member_id).execute()
        
        if not presence_data.data:
            return False, "Aucune donnée de présence trouvée pour ce membre"
        
        # 2. Supprimer les enregistrements de présence pour libérer la clé étrangère
        supabase.table("fact_presence_au_culte").delete().eq("member_id", member_id).execute()
        
        # 3. Mettre à jour l'ID du membre dans dim_membres
        supabase.table("dim_membres").update({
            "member_id": new_member_id,
            "type_membre": "MEMBRE"
        }).eq("member_id", member_id).execute()
        
        # 4. Préparer les données pour une insertion massive
        bulk_data = []
        for record in presence_data.data:
            new_record = record.copy()
            new_record["member_id"] = new_member_id
            new_record["souhaite_rester"] = True
            # Supprimer l'ID pour éviter les conflits lors de l'insertion
            if "id" in new_record:
                del new_record["id"]
            bulk_data.append(new_record)
        
        # 5. Réinsérer toutes les données en une seule opération
        if bulk_data:
            supabase.table("fact_presence_au_culte").insert(bulk_data).execute()
        
        return True, new_member_id
    except Exception as e:
        return False, str(e)

# Style CSS personnalisé
st.markdown("""
<style>
    /* Style pour les boutons de navigation et de confirmation */
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #E6E6E6;
        color: black;
        border: none !important;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #4da6ff;
        color: white;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Créer la barre latérale pour la navigation
with st.sidebar:
    st.image("assets/EDC_logo_white.jpg", width=100)
    st.title("Menu")
    
    # Boutons de navigation avec style conditionnel
    if st.button("📝 Liste de Présence", 
                key="btn_attendance", 
                use_container_width=True,
                type="primary" if st.session_state.page == "attendance" else "secondary"):
        st.session_state.page = "attendance"
        st.rerun()
    
    if st.button("👋 Nouvelles Personnes", 
                key="btn_visitors", 
                use_container_width=True,
                type="primary" if st.session_state.page == "new_visitors" else "secondary"):
        st.session_state.page = "new_visitors"
        st.rerun()

# Page d'enregistrement de présence
if st.session_state.page == "attendance":
    # En-tête avec titre et logo
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📝 Liste de Présence au Culte")
    with col2:
        st.image("assets/EDC_logo_white.jpg", width=100)
    
    st.write("")
    st.write("")
    st.markdown("<div style='text-align: left; font-size: 24px; font-weight: normal;'>Bienvenue au culte à l'église Édifice Du Christ</div>", unsafe_allow_html=True)
    st.write("")
    st.write("Veuillez entrer vos informations de contact")
    st.write("")

    # Formulaire principal
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
        
        submit_button = st.form_submit_button("Confirmer présence")

    # Conteneur pour les messages
    message_container = st.container()

    # Traitement du formulaire
    if submit_button:
        st.session_state.validation_errors = {}
        st.session_state.show_success = False
        st.session_state.show_warning = False
        
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
        
        if input_valid:
            nom_formate = nom.strip().upper()
            prenoms_formate = prenoms.strip().title()
            contact_formate = format_phone_number(contact.strip())
            email_formate = email_lower if email_lower else None
            lieu_habitation_formate = lieu_habitation.strip().title()
            
            # Déterminer le type_membre et le member_id
            if first_time == "Oui":
                type_membre = 'INVITE'
                member_id = generate_temp_id()
            else:
                type_membre = 'MEMBRE'
                member_id = generate_member_id()
            
            try:
                # Vérifier si le membre existe déjà
                response = supabase.table("dim_membres").select("member_id", "date_de_premier_culte").eq("nom", nom_formate).eq("prenoms", prenoms_formate).execute()
                
                if response.data:
                    member_id = response.data[0]["member_id"]
                    date_premier_culte = response.data[0]["date_de_premier_culte"]
                    
                    # Mettre à jour les informations si nécessaire
                    update_data = {}
                    if contact_formate:
                        update_data["contact"] = contact_formate
                    if email_formate:
                        update_data["email"] = email_formate
                    if lieu_habitation_formate:
                        update_data["lieu_d_habitation"] = lieu_habitation_formate
                    
                    if update_data:
                        supabase.table("dim_membres").update(update_data).eq("member_id", member_id).execute()
                else:
                    # Nouveau membre
                    est_nouveau = True
                    date_premier_culte = date.today().isoformat() if first_time == "Oui" else None
                    
                    supabase.table("dim_membres").insert({
                        "member_id": member_id,
                        "type_membre": type_membre,
                        "nom": nom_formate,
                        "prenoms": prenoms_formate,
                        "sexe": sexe,
                        "date_de_naissance": date_naissance.isoformat(),
                        "contact": contact_formate,
                        "email": email_formate,
                        "lieu_d_habitation": lieu_habitation_formate,
                        "date_de_premier_culte": date_premier_culte
                    }).execute()

                # Enregistrement de la présence
                today_str = date.today().isoformat()
                presence_response = supabase.table("fact_presence_au_culte").select("member_id", count="exact").eq("member_id", member_id).eq("date", today_str).execute()
                
                if presence_response.count == 0:
                    supabase.table("fact_presence_au_culte").insert({
                        "member_id": member_id,
                        "nom": nom_formate,
                        "prenoms": prenoms_formate,
                        "date": today_str,
                        "est_nouveau": first_time == "Oui",
                        "est_present": True,
                        "souhaite_rester": False  # Valeur par défaut
                    }).execute()
                    st.session_state.show_success = True
                    st.session_state.form_submitted = True
                else:
                    st.session_state.show_warning = True
                    
            except Exception as e:
                error_message = str(e)
                if hasattr(e, 'code') and e.code == '23505':
                    if 'contact' in error_message:
                        st.session_state.validation_errors["db_error"] = "Ce numéro de téléphone existe déjà, veuillez en mettre un autre"
                    elif 'email' in error_message:
                        st.session_state.validation_errors["db_error"] = "Cet email existe déjà, veuillez en mettre un autre"
                    else:
                        st.session_state.validation_errors["db_error"] = "Erreur de doublon dans la base de données"
                else:
                    st.session_state.validation_errors["db_error"] = f"Erreur lors de l'enregistrement: {error_message}"

    # Affichage des messages uniquement si aucune réinitialisation n'est demandée
    if not st.session_state.reset_requested:
        with message_container:
            if st.session_state.validation_errors:
                for error_msg in st.session_state.validation_errors.values():
                    st.error(f"Erreur : {error_msg}")
                if st.button("Corriger les erreurs", key="fix_errors"):
                    st.session_state.reset_requested = True
                    st.rerun()

            if st.session_state.show_success:
                st.success("✅ Présence confirmée et membre enregistré !")
                if st.button("Nouvelle saisie", key="new_entry"):
                    st.session_state.reset_requested = True
                    st.rerun()

            if st.session_state.show_warning:
                st.warning("⚠️ Ce membre est déjà enregistré pour aujourd'hui !")
                if st.button("Retour à l'accueil", key="return_home"):
                    st.session_state.reset_requested = True
                    st.rerun()

# Page des nouvelles personnes
elif st.session_state.page == "new_visitors":
    st.title("👋 Liste des Nouvelles Personnes")
    st.write("Cochez les cases pour sélectionner les invités qui souhaitent devenir membres permanents.")
    
    # Obtenir la liste des nouveaux visiteurs (TEMP*)
    try:
        # Récupérer les informations des invités
        response = supabase.table("dim_membres").select("*").eq("type_membre", "INVITE").execute()
        new_visitors = response.data
        
        if new_visitors:
            # Créer un dictionnaire pour stocker l'état des cases à cocher s'il n'existe pas déjà
            if "visitor_checkboxes" not in st.session_state:
                st.session_state.visitor_checkboxes = {}
            
            # Créer une colonne de filtrage par date
            st.write("Filtrer par date de culte :")
            col_date, col_apply = st.columns([3, 1])
            with col_date:
                filter_date = st.date_input(
                    "Date",
                    value=date.today(),
                    label_visibility="collapsed"
                )
            with col_apply:
                apply_filter = st.button("Appliquer", use_container_width=True)

            # En-tête du tableau
            st.markdown("---")
            col_headers = st.columns([3, 3, 3, 2, 1])
            col_headers[0].markdown("<b>Nom et Prénoms</b>", unsafe_allow_html=True)
            col_headers[1].markdown("<b>Lieu d'habitation</b>", unsafe_allow_html=True)
            col_headers[2].markdown("<b>Contact</b>", unsafe_allow_html=True)
            col_headers[3].markdown("<b>Premier culte</b>", unsafe_allow_html=True)
            col_headers[4].markdown("<b>Souhaite rester</b>", unsafe_allow_html=True)
            st.markdown("---")
            
            # Préparer les données pour l'affichage
            table_data = []
            for visitor in new_visitors:
                member_id = visitor["member_id"]
                date_premier_culte = visitor.get("date_de_premier_culte")
                
                # Appliquer le filtre de date si demandé
                if apply_filter and date_premier_culte and date_premier_culte != filter_date.isoformat():
                    continue
                
                # Obtenir l'état actuel du champ souhaite_rester dans la base de données
                presence_response = supabase.table("fact_presence_au_culte").select("souhaite_rester").eq("member_id", member_id).execute()
                souhaite_rester = False
                if presence_response.data:
                    souhaite_rester = presence_response.data[0].get("souhaite_rester", False)
                
                # Initialiser l'état de la case à cocher dans session_state s'il n'existe pas
                if member_id not in st.session_state.visitor_checkboxes:
                    st.session_state.visitor_checkboxes[member_id] = souhaite_rester
                
                table_data.append({
                    "member_id": member_id,
                    "nom": visitor["nom"],
                    "prenoms": visitor["prenoms"],
                    "lieu_d_habitation": visitor.get("lieu_d_habitation", ""),
                    "contact": visitor.get("contact", ""),
                    "date_de_premier_culte": date_premier_culte
                })
            
            if table_data:
                # Afficher les données dans le tableau
                for visitor in table_data:
                    cols = st.columns([3, 3, 3, 2, 1])
                    
                    with cols[0]:
                        st.write(f"**{visitor['nom']} {visitor['prenoms']}**")
                    
                    with cols[1]:
                        st.write(visitor['lieu_d_habitation'])
                    
                    with cols[2]:
                        st.write(visitor['contact'])
                    
                    with cols[3]:
                        if visitor['date_de_premier_culte']:
                            date_obj = datetime.strptime(visitor['date_de_premier_culte'], "%Y-%m-%d")
                            st.write(date_obj.strftime("%d/%m/%Y"))
                        else:
                            st.write("N/A")
                    
                    with cols[4]:
                        checkbox_key = f"checkbox_{visitor['member_id']}"
                        st.session_state.visitor_checkboxes[visitor['member_id']] = st.checkbox("", 
                                                                                    value=st.session_state.visitor_checkboxes[visitor['member_id']], 
                                                                                    key=checkbox_key)
                
                # Bouton pour convertir en masse les invités sélectionnés
                st.markdown("---")
                
                # Alignement à gauche pour le bouton de conversion
                col_button, col_empty = st.columns([2, 3])
                with col_button:
                    if st.button("Confirmer les conversions en membres", type="primary", use_container_width=True):
                        selected_visitors = [id for id, selected in st.session_state.visitor_checkboxes.items() if selected]
                        
                        if not selected_visitors:
                            st.warning("Veuillez sélectionner au moins un invité à convertir.")
                        else:
                            success_count = 0
                            errors = []
                            
                            # Convertir chaque invité sélectionné
                            for member_id in selected_visitors:
                                success, result = convert_visitor_to_member(member_id)
                                if success:
                                    success_count += 1
                                else:
                                    errors.append(f"Erreur pour {member_id}: {result}")
                            
                            # Afficher les résultats
                            if success_count > 0:
                                st.success(f"✅ {success_count} invité(s) converti(s) en membres avec succès!")
                            
                            if errors:
                                for error in errors:
                                    st.error(error)
                            
                            # Réinitialiser les cases à cocher et recharger la page
                            if success_count > 0:
                                st.session_state.visitor_checkboxes = {}
                                st.rerun()
            else:
                st.info("Aucun visiteur correspondant au filtre sélectionné.")
        else:
            st.info("Aucune nouvelle personne enregistrée pour le moment.")
    
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données: {e}")