# NBA Analyst AI — Assistant RAG + SQL (Gemini)

Assistant virtuel pour analystes/entraîneurs NBA, développé pour **SportSee** (cf. [`mission.md`](mission.md)). Il combine deux sources de contexte pour répondre aux questions :

- une **base de connaissances textuelle** (discussions Reddit sur la ligue) interrogée par recherche vectorielle (FAISS) ;
- une **base de statistiques joueurs** (issue d'un fichier Excel) interrogée en SQL.

Un agent [Pydantic AI](https://pydantic.dev/docs/ai/overview/) (modèle **Google Gemini**) choisit dynamiquement quelle(s) source(s) interroger, puis synthétise une réponse sourcée.

> 📖 Pour l'architecture détaillée, le rôle de chaque module, le pipeline d'évaluation et les limitations connues, voir **[`documentation.md`](documentation.md)**.

## Fonctionnalités

- 🔍 **Recherche sémantique** (FAISS + embeddings Gemini) sur des documents indexés depuis `inputs/`
- 🧮 **Tool SQL** : l'agent interroge une base SQLite de statistiques joueurs (par nom de joueur ou requête libre générée par le LLM)
- ✅ **Entrées/sorties validées par Pydantic** à chaque étape du pipeline (documents, chunks, embeddings, réponses)
- 📊 **Évaluation automatisée** du système (Pydantic Evals, LLM-judge) : fidélité, pertinence, précision et rappel du contexte récupéré
- 🔭 **Traçabilité** via Pydantic Logfire (chaque appel de tool, requête et réponse)

## Prérequis

- Python 3.13+
- Une clé API Google Gemini ([aistudio.google.com](https://aistudio.google.com/))

## Installation

```bash
git clone git@github.com:AunCly/p10_evaluate_llm_performances.git
cd p10_evaluate_llm_performances

# avec uv (recommandé)
uv sync
```

Créer un fichier `.env` à la racine :

```dotenv
GOOGLE_API_KEY=votre_clé_api_google
MODEL_ID=gemini-3.5-flash-lite
EMBEDDING_MODEL=gemini-embedding-001
INPUT_DIR=inputs
OUTPUT_DIR=vector_db
FAISS_INDEX_FILE=vector_db/faiss_index.idx
DOCUMENT_CHUNKS_FILE=vector_db/document_chunks.pkl
```

> `requirements.txt` correspond à une version antérieure du projet (Mistral/LangChain) et n'est plus à jour ; `pyproject.toml` est la source de vérité pour les dépendances.

## Structure du projet

```
.
├── chat.py               # Application Streamlit (UI de chat)
├── indexer.py             # Indexation des documents (construction de l'index FAISS)
├── database/               # Schéma SQL, création et modèles ORM de la base de stats
├── inputs/                 # Documents sources (PDF, Excel)
├── vector_db/               # Index FAISS et chunks (générés par indexer.py)
├── schemas/                 # Modèles Pydantic (validation des entrées/sorties)
└── utils/
    ├── config.py            # Configuration (.env, chemins, constantes)
    ├── data_loader.py        # Extraction de texte multi-format (+ OCR)
    ├── vector_store.py        # Index FAISS et recherche sémantique
    ├── load_excel_to_db.py     # Ingestion du fichier Excel vers la base SQLite
    ├── rag.py                  # Agent Pydantic AI (RAG + SQL)
    └── evaluate.py              # Évaluation du système (Pydantic Evals)
```

## Utilisation

```bash
# 1. Créer et peupler la base de statistiques (une fois)
python database/create_database.py
python -m utils.load_excel_to_db

# 2. Construire l'index vectoriel à partir des documents de inputs/ (une fois, ou après ajout de documents)
python indexer.py

# 3. Lancer l'interface de chat
streamlit run chat.py
```

L'application est accessible sur http://localhost:8501.

### Évaluer le système

```bash
python -m utils.evaluate
```

Exécute le pipeline RAG+SQL sur un jeu de questions métier et note les réponses (fidélité, pertinence, précision/rappel du contexte récupéré) via un LLM-judge Gemini.

## Pour aller plus loin

- [`documentation.md`](documentation.md) — documentation technique complète (architecture détaillée, schéma de base de données, pipeline d'indexation, évaluation, limitations connues)
- [`mission.md`](mission.md) — brief de mission et choix techniques validés
- [`plan.md`](plan.md) — plan de mise en œuvre et audit détaillé du prototype initial
