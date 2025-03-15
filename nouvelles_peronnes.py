import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Nouvelles Personnes", layout="wide")

# Connexion à Supabase
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["key"]
supabase: Client = create_client(supabase_url, supabase_key)

# Fonction pour générer un nouvel identifiant de membre (MEMBER00X)
def generate_member_id():
    try:
        # Récupérer tous les member_id commençant par MEMBER
        response = supabase.table("dim_membres").select("member_id").execute()
        member_ids = [entry['member_id'] for entry in response.data if entry['member_id'].startswith('MEMBER')]
        if member_ids:
            # Trouver le plus grand numéro parmi les MEMBER00X
            max_num = max(int(id.replace("MEMBER", "")) for id in member_ids)
            count = max_num + 1
        else:
            count = 1
        return f"MEMBER{count:03d}"  # Exemple : MEMBER001, MEMBER002, etc.
    except Exception as e:
        st.error(f"Erreur lors de la génération de l'ID membre: {e}")
        return None

# Récupérer les nouvelles personnes (type_membre = 'INVITE')
response = supabase.table("dim_membres").select("member_id", "nom", "prenoms", "lieu_d_habitation", "contact", "date_de_premier_culte").eq("type_membre", "INVITE").execute()
data = response.data

if data:
    # Préparer les données dans un DataFrame
    df = pd.DataFrame(data)
    df["souhaite_rester"] = False  # Ajouter une colonne pour les cases à cocher

    # Afficher la table avec des cases à cocher
    edited_df = st.data_editor(
        df,
        column_config={
            "souhaite_rester": st.column_config.CheckboxColumn("Souhaite rester")
        },
        hide_index=True
    )

    # Bouton pour valider les changements
    if st.button("Valider les changements"):
        for index, row in edited_df.iterrows():
            if row["souhaite_rester"]:
                old_member_id = row["member_id"]  # Ex: TEMP001
                new_member_id = generate_member_id()  # Ex: MEMBER001
                if new_member_id:
                    try:
                        # Étape 1 : Mise à jour de fact_presence_au_culte
                        supabase.table("fact_presence_au_culte").update({
                            "member_id": new_member_id
                        }).eq("member_id", old_member_id).execute()

                        # Étape 2 : Mise à jour de dim_membres
                        supabase.table("dim_membres").update({
                            "member_id": new_member_id,
                            "type_membre": "MEMBRE"
                        }).eq("member_id", old_member_id).execute()

                        st.success(f"{row['nom']} {row['prenoms']} est maintenant un membre avec l'ID {new_member_id}.")
                    except Exception as e:
                        st.error(f"Erreur lors de la mise à jour pour {row['nom']} {row['prenoms']}: {e}")
else:
    st.write("Aucune nouvelle personne à afficher.")