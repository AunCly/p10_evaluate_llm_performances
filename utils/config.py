# utils/config.py
import os
from dotenv import load_dotenv

# Racine du projet (indépendante du répertoire courant depuis lequel le script est lancé)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Charger les variables d'environnement du fichier .env
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Clé API ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("⚠️ Attention: La clé API Google (GOOGLE_API_KEY) n'est pas définie dans le fichier .env")
    # Vous pouvez choisir de lever une exception ici ou de continuer avec des fonctionnalités limitées
    # raise ValueError("Clé API Google manquante. Veuillez la définir dans le fichier .env")

# --- Modèles Google ---
EMBEDDING_MODEL = "gemini-embedding-001"
MODEL_NAME = "gemini-3.5-flash-lite" # Ou un autre modèle comme gemini-3.7-flash

# --- Configuration de l'Indexation ---
# INPUT_DATA_URL = os.getenv("INPUT_DATA_URL") # Décommentez si vous utilisez une URL
INPUT_DIR = os.path.join(BASE_DIR, "inputs")            # Dossier pour les données sources après extraction
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")      # Dossier pour stocker l'index Faiss et les chunks
FAISS_INDEX_FILE = os.path.join(VECTOR_DB_DIR, "faiss_index.idx")
DOCUMENT_CHUNKS_FILE = os.path.join(VECTOR_DB_DIR, "document_chunks.pkl")

CHUNK_SIZE = 1500                   # Taille des chunks en *caractères* (vise ~512 tokens)
CHUNK_OVERLAP = 150                 # Chevauchement en *caractères*
EMBEDDING_BATCH_SIZE = 32           # Taille des lots pour l'API d'embedding

# --- Configuration de la Recherche ---
SEARCH_K = 5                        # Nombre de documents à récupérer par défaut

# --- Configuration de la Base de Données ---
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_FILE = os.path.join(DATABASE_DIR, "interactions.db")
DATABASE_URL = f"sqlite:///{DATABASE_FILE}" # URL pour SQLAlchemy

# --- Configuration de l'Application ---
APP_TITLE = "NBA Analyst AI"
NAME = "NBA" # Nom à personnaliser dans l'interface