# MistralChat.py (version RAG)
import streamlit as st
import logging

# --- Importations depuis vos modules ---
try:
    from utils.config import APP_TITLE, NAME
    from utils.rag import Rag
except ImportError as e:
    st.error(f"Erreur d'importation: {e}. Vérifiez la structure de vos dossiers et les fichiers dans 'utils'.")
    st.stop()


# --- Configuration du Logging ---
# Note: Streamlit peut avoir sa propre gestion de logs. Configurer ici est une bonne pratique.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# --- Chargement du pipeline RAG (mis en cache) ---
@st.cache_resource # Garde le pipeline chargé en mémoire pour la session
def get_rag() -> Rag | None:
    logging.info("Tentative d'initialisation du pipeline RAG...")
    try:
        rag = Rag()
        logging.info(f"Pipeline RAG initialisé avec succès ({rag.vector_store.index.ntotal} vecteurs).")
        return rag
    except (ValueError, RuntimeError) as e:
        st.error(f"Erreur lors de l'initialisation du pipeline RAG : {e}")
        st.warning("Assurez-vous d'avoir exécuté 'python indexer.py' après avoir placé vos fichiers dans le dossier 'inputs'.")
        logging.error(f"Échec de l'initialisation de Rag(): {e}")
        return None
    except Exception as e:
        st.error(f"Erreur inattendue lors du chargement du pipeline RAG: {e}")
        logging.exception("Erreur chargement Rag()")
        return None

rag = get_rag()

# --- Initialisation de l'historique de conversation ---
if "messages" not in st.session_state:
    # Message d'accueil initial
    st.session_state.messages = [{"role": "assistant", "content": f"Bonjour ! Je suis votre analyste IA pour la {NAME}. Posez-moi vos questions sur les équipes, les joueurs ou les statistiques, et je vous répondrai en me basant sur les données les plus récentes."}]

# --- Interface Utilisateur Streamlit ---
st.title(APP_TITLE)
st.caption(f"Assistant virtuel pour {NAME} | Modèle: {rag.model if rag else 'indisponible'}")

# Affichage des messages de l'historique (pour l'UI)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Zone de saisie utilisateur
if prompt := st.chat_input(f"Posez votre question sur la {NAME}..."):
    # 1. Ajouter et afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. Vérifier si le pipeline RAG est disponible
    if rag is None:
        st.error("Le service de recherche de connaissances n'est pas disponible. Impossible de traiter votre demande.")
        logging.error("Pipeline RAG non disponible pour la recherche.")
        st.stop()

    # 3. Exécuter le pipeline RAG (recherche + génération) et afficher la réponse
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.text("...") # Indicateur simple

        rag_answer = rag.answer(prompt)
        response_content = rag_answer.answer

        message_placeholder.write(response_content)

    # 4. Ajouter la réponse de l'assistant à l'historique (pour affichage UI)
    st.session_state.messages.append({"role": "assistant", "content": response_content})

# Petit pied de page optionnel
st.markdown("---")
st.caption("Powered by Google Gemini & Faiss | Data-driven NBA Insights")
