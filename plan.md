# Plan de mise en œuvre — Audit, extension et documentation du prototype RAG SportSee

> Basé sur `mission.md` (brief de Sarah) et sur l'audit du code existant effectué le 2026-09-10.
> Objectif final : produire, dans ce repo Git, le **Rapport de mise en place et d'évaluation du système RAG**, avec à l'appui tout le code, les jeux de tests et les résultats chiffrés.

---

## 0. Audit de l'existant (fait, résumé)

### 0.1 Ce qui existe déjà
| Fichier | Rôle actuel | Constat |
|---|---|---|
| `MistralChat.py` | UI Streamlit, RAG "1 shot" (recherche FAISS → prompt unique → `client.chat`) | Utilise le **SDK `mistralai==0.4.2`** (API legacy `MistralClient`/`ChatMessage`, dépréciée). Pas d'agent, pas de tool, pas de structuration des entrées/sorties. Un seul gros prompt texte, pas de séparation system/user. |
| `indexer.py` | CLI d'indexation (charge `inputs/`, splitte, embed, sauvegarde FAISS) | Fonctionnel, mais couplé à Mistral pour les embeddings. |
| `utils/vector_store.py` | `VectorStoreManager` : split (Langchain `RecursiveCharacterTextSplitter`), embeddings Mistral, index FAISS `IndexFlatIP` (cosinus), recherche top-k | Pas de validation Pydantic des entrées/sorties. Gestion d'erreurs par vecteurs nuls en cas d'échec d'embedding (silencieux, peut fausser la recherche). |
| `utils/data_loader.py` | Extraction texte multi-format (PDF, DOCX, TXT, CSV, XLSX) + **fallback OCR EasyOCR** sur PDF scannés | Les PDF fournis (`Reddit 1-4.pdf`) sont des **captures d'écran de threads Reddit** (aucun texte natif extractible — vérifié, `PdfReader` renvoie vide) → **100% du pipeline texte dépend de l'OCR**, donc le texte indexé est **bruité** (résidus de pub "adidas_Ecom_Europe", UI Reddit, doublons d'en-têtes, fautes d'OCR). C'est une donnée de test "bruitée" très représentative. |
| `utils/config.py` | Config statique (clé Mistral, tailles de chunk, chemins) | À migrer vers Gemini + à étendre (DB, Logfire). |
| `vector_db/*.pkl/.idx` | Index déjà construit (302 chunks, embeddings Mistral) | **À régénérer** après migration des embeddings vers Gemini (les vecteurs ne sont pas comparables entre modèles). |
| `inputs/regular NBA.xlsx` | Données chiffrées | Voir audit détaillé ci-dessous — **limitation majeure à documenter**. |
| `main.py` | Stub `uv init` non utilisé | Sera remplacé par un vrai point d'entrée CLI ou supprimé. |
| `.env` | Contient déjà `GOOGLE_API_KEY`, `MODEL_ID`, `EMBEDDING_MODEL`, `INPUT_DIR`, `OUTPUT_DIR`, `FAISS_INDEX_FILE`, `DOCUMENT_CHUNKS_FILE` | Confirme que la bascule vers Gemini était déjà anticipée — `utils/config.py` doit être aligné sur ces noms de variables. |
| venv (`uv pip list`) | `pydantic 2.13`, `pydantic-ai-slim 2.42`, `pydantic-settings`, `google-genai 2.22`, `sqlalchemy 2.0`, `logfire-api` (stub), `ragas 0.4.3`, `mistralai 0.4.2` déjà installés, **mais absents de `pyproject.toml`** | Il faudra nettoyer/figer les dépendances réelles dans `pyproject.toml` (ajouter les manquantes, retirer `mistralai`/`ragas`/`langchain*` une fois la migration terminée). `logfire-api` est un stub sans backend : il faudra le paquet complet `logfire`. `pydantic-evals` n'est pas installé. |

### 0.2 Audit du fichier `inputs/regular NBA.xlsx` (critique pour l'étape 2)
5 feuilles :
- **`Données NBA`** (570 lignes × 53 colonnes, header en ligne 2) : **statistiques agrégées par joueur sur l'ensemble de la saison régulière** (Player, Team, Age, GP, W, L, Min, PTS, FG%, 3P%, REB, AST, OFFRTG, DEFRTG, PIE, etc.).
- **`Equipe`** : table de correspondance `Code` (3 lettres) → `Nom complet de l'équipe` (30 lignes).
- **`Dictionnaire des données`** : description métier de chaque colonne (45 lignes) → **à réutiliser comme documentation du schéma**.
- **`Analyse` / `Analyse Vide`** : feuilles de restitution vides (templates Excel), non exploitables comme données sources.

> ⚠️ **Limitation de données majeure, à documenter explicitement dans le rapport final (et anticipée comme point d'analyse des biais de l'étape 3)** :
> Le fichier Excel ne contient **que des agrégats saison par joueur**. Il n'y a **aucune donnée match par match**, ni **domicile/extérieur**, ni historique temporel. Les questions métier citées en exemple par Sarah — *"meilleur % à 3 points sur les 5 derniers matchs"*, *"comparer les rebonds domicile/extérieur"* — **ne sont pas littéralement répondables avec ces données**. Il faut :
> 1. Garder ces questions comme **cas de test "limite/hors-couverture"** (elles sont précieuses justement pour *révéler* cette limite en étape 1 et la documenter en étape 3).
> 2. Définir en parallèle un **jeu de questions "réalistes"** strictement répondables avec les colonnes disponibles (comparaisons saison, classements, ratios, agrégations par équipe), qui serviront de base principale à l'évaluation SQL de l'étape 2.
> 3. Ne **pas fabriquer** de fausses données match-par-match ou domicile/extérieur pour combler artificiellement — ce serait trompeur pour un rapport destiné à la production. La table `matches` du schéma (étape 2) sera donc modélisée (DDL documenté) mais **non peuplée** par ce jeu de données, avec une note explicite de limite/extension future.
> 4. Il n'existe pas de **table "reports" métier** au sens tabulaire — seuls les 4 PDF Reddit jouent ce rôle (archives textuelles). La table `reports` servira donc de **registre de traçabilité** des documents indexés dans le vector store (id, source, catégorie, date d'ingestion), pas de contenu métier basket.

### 0.3 Choix techniques déjà arbitrés par Sarah/la mentor (repris tels quels)
- ❌ RAGAS (abandonné, incompatible Langchain récent) → remplacé par **Pydantic Evals**.
- ✅ **Pydantic** pour valider entrées/sorties du pipeline RAG et SQL.
- ✅ **Pydantic AI** à la place de Langchain pour l'orchestration agent/tools.
- ✅ **Pydantic Logfire** pour l'observabilité pas-à-pas de la chaîne RAG/LLM.
- ✅ **Pydantic Evals** pour l'évaluation.
- ✅ **Google Gemini** à la place de Mistral (génération **et** embeddings).

### 0.4 Dépendances à ajouter / nettoyer (`pyproject.toml`)
À ajouter (via `uv add`) :
- `pydantic-ai-slim[google]` (ou `pydantic-ai` complet) — agent + tool calling + intégration Gemini
- `pydantic-evals` — framework d'évaluation (cases, evaluators, rapport)
- `logfire` (paquet complet, pas seulement `logfire-api`) — export des traces
- `google-genai` (déjà présent) — client Gemini (chat + embeddings)
- `sqlalchemy` (déjà présent) — ORM pour `players/matches/stats/reports`
- `pydantic-settings` (déjà présent) — config typée (remplace `utils/config.py` "à la main")
- `matplotlib` ou `plotly` — graphiques du rapport comparatif (étape 3)

À retirer une fois la migration validée : `mistralai`, `ragas`, `langchain`, `langchain-community`, `langchain-openai` (on garde éventuellement `langchain-text-splitters` seul si on réutilise le splitter, sinon on le remplace par un split Pydantic AI/maison pour limiter les dépendances).

---

## 1. Architecture cible (vue d'ensemble)

```
.
├── pyproject.toml                  # deps nettoyées (Gemini, Pydantic AI/Evals, Logfire, SQLAlchemy)
├── .env                            # GOOGLE_API_KEY, MODEL_ID, EMBEDDING_MODEL, DATABASE_URL, LOGFIRE_TOKEN
├── utils/
│   ├── config.py                   # migré vers pydantic-settings (Gemini + DB + Logfire)
│   ├── data_loader.py              # conservé (OCR + extraction), annoté sur le bruit connu
│   └── vector_store.py             # migré : embeddings Gemini, + validation Pydantic des chunks/résultats
├── schemas/
│   ├── documents.py                # modèles Pydantic: RawDocument, Chunk, EmbeddedChunk
│   └── rag_io.py                   # modèles Pydantic: RagQuery, RagAnswer, RetrievedContext
├── db/
│   ├── models.py                   # SQLAlchemy ORM: Player, Team, Stat, Match (vide), Report
│   ├── schema.sql                  # DDL documenté + commentaires métier
│   └── nba.db                      # sqlite (gitignored)
├── load_excel_to_db.py             # Étape 2 : Excel -> validation Pydantic -> insertion DB
├── sql_tool.py                     # Étape 2 : tool Pydantic AI, NL -> SQL (few-shot) -> exécution -> résultats typés
├── agent.py                        # Agent Pydantic AI unique : tool RAG + tool SQL, routage, synthèse
├── indexer.py                      # adapté : embeddings Gemini, inchangé dans l'esprit
├── app.py                          # ex-MistralChat.py, UI Streamlit branchée sur agent.py
├── evals/
│   ├── dataset.py                  # jeu de questions catégorisées (simples/complexes/bruitées/mixtes/hors-couverture)
│   ├── evaluators.py               # evaluators Pydantic Evals (LLM-judge Gemini : pertinence, fidélité, exactitude SQL)
│   └── results/                    # sorties horodatées (avant/après enrichissement SQL)
├── evaluate_ragas.py               # script d'évaluation (nom conservé par cohérence avec le brief), moteur = Pydantic Evals
└── reports/
    └── rapport_evaluation_rag.md   # livrable final (synthèse + tableaux + graphiques)
```

Flux agent cible :
```
Question utilisateur
   │
   ▼
Agent Pydantic AI (Gemini) ── décide via system prompt + description des tools
   ├── si besoin de contexte textuel  → tool "search_knowledge_base" (RAG / FAISS)
   ├── si besoin de données chiffrées → tool "query_stats" (NL→SQL sur SQLite)
   └── peut combiner les deux pour une question mixte
   │
   ▼
Synthèse finale (réponse sourcée : extraits RAG + résultats SQL)
   │
   ▼
Logfire : trace de chaque étape (requête, tool appelé, contexte récupéré, SQL exécuté, réponse)
```

---

## 2. Étape 1 — Évaluation structurée du prototype existant

### 2.1 Pipeline de préparation des données, sécurisé par Pydantic
- [ ] **`schemas/documents.py`** : modèles `RawDocument` (source, category, texte brut), `Chunk` (id, texte, métadonnées, longueur) avec validateurs (texte non vide, longueur min/max cohérente avec `CHUNK_SIZE`), `EmbeddedChunk` (vecteur + dimension attendue).
- [ ] Refonte **`utils/vector_store.py`** :
  - remplacer le client Mistral par `google-genai` pour les embeddings (modèle lu depuis `EMBEDDING_MODEL` du `.env`) ;
  - faire passer chaque chunk par `Chunk.model_validate(...)` avant embedding, et chaque résultat de recherche par un modèle `RetrievedContext` avant de remonter à l'agent (garantit score dans [0,100], texte non vide, métadonnées `source` présente) ;
  - logguer (Logfire) les cas de rejet de validation plutôt que de les avaler silencieusement (contrairement au comportement actuel des embeddings ratés → vecteurs nuls).
- [ ] **`indexer.py`** : adapter l'import (embeddings Gemini), régénérer `vector_db/faiss_index.idx` et `document_chunks.pkl`.
- [ ] **`schemas/rag_io.py`** : `RagQuery` (question utilisateur validée : non vide, longueur max) et `RagAnswer` (réponse + liste des sources citées + confiance) — ce sont les entrées/sorties *du tool RAG*, validées à chaque appel.

### 2.2 Intégration Pydantic Logfire
- [ ] Instrumenter `agent.py` (et `vector_store.py`) avec `logfire.instrument_pydantic_ai()` et des spans explicites : `search_knowledge_base`, `embedding_query`, `llm_generation`.
- [ ] Vérifier dans le dashboard Logfire (local ou cloud) que l'on voit, pour une question donnée : la requête → les chunks récupérés (avec scores) → le prompt final envoyé à Gemini → la réponse.
- [ ] Capturer une capture d'écran (ou export) du trace Logfire pour illustration dans le rapport final (§ traçabilité).

### 2.3 Script d'évaluation `evaluate_ragas.py` (moteur Pydantic Evals)
- [ ] **`evals/dataset.py`** : constituer le jeu de questions métier, catégorisé :

  | Catégorie | Exemples | Ce qu'elle teste |
  |---|---|---|
  | **Simple (factuel RAG)** | "De quoi parle la discussion Reddit sur l'avantage du terrain en finale NBA ?" | Récupération + synthèse directe |
  | **Complexe (RAG multi-sources)** | "Quels sont les arguments soulevés dans les threads Reddit concernant [sujet X] ?" | Agrégation de plusieurs chunks |
  | **Bruitée** | Questions posées en langage familier/fautes, ou dont la réponse est diluée dans un OCR bruité | Robustesse au bruit OCR déjà identifié (§0.2) |
  | **Chiffrée (hors-couverture RAG pur)** | "Quel joueur a le meilleur % à 3 points sur les 5 derniers matchs ?", "Compare les rebonds domicile/extérieur" | **Doit échouer ou halluciner en étape 1** (pas de Tool SQL encore) → baseline de référence pour l'étape 3 |
  | **Chiffrée réaliste (couverte par les données)** | "Quel joueur a le meilleur PIE de la saison ?", "Quelle équipe a le plus de victoires ?" | Même constat : RAG seul ne peut pas requêter le tableur |

- [ ] **`evals/evaluators.py`** : definir les evaluators Pydantic Evals — a minima un **LLM-judge** (Gemini) pour la pertinence/fidélité (grounding dans le contexte récupéré), + des evaluators déterministes (présence de la source citée, temps de réponse, absence de refus).
- [ ] **`evaluate_ragas.py`** : charge le dataset, exécute l'agent (RAG seul, étape 1) sur chaque cas, calcule les scores, exporte `evals/results/eval_baseline_<date>.json` + un tableau récapitulatif (Markdown ou CSV).
- [ ] Synthétiser dans le rapport un **tableau comparatif catégorie × score moyen**, avec commentaire qualitatif par catégorie (notamment : confirmation que les questions chiffrées échouent sans Tool SQL → justifie l'étape 2).

---

## 3. Étape 2 — Intégration des données Excel et Tool SQL

### 3.1 Modélisation de la base (SQLite)
- [ ] **`db/schema.sql`** (DDL documenté, commentaires issus de la feuille `Dictionnaire des données`) :
  - `teams (code PK, full_name)` ← feuille `Equipe`
  - `players (id PK, name, team_code FK→teams, age)`
  - `stats (id PK, player_id FK→players, season, gp, w, l, min, pts, fgm, fga, fg_pct, 3pa, 3p_pct, ftm, fta, ft_pct, oreb, dreb, reb, ast, tov, stl, blk, pf, fp, dd2, td3, plus_minus, offrtg, defrtg, netrtg, ast_pct, ast_to, ast_ratio, oreb_pct, dreb_pct, reb_pct, to_ratio, efg_pct, ts_pct, usg_pct, pace, pie, poss)` — une ligne = agrégat saison d'un joueur (1 seule saison disponible ici, colonne `season` prévue pour l'évolutivité)
  - `matches (id PK, season, date, home_team_code FK, away_team_code FK, home_score, away_score)` — **schéma prêt mais table vide** (cf. limitation §0.2), avec commentaire DDL explicite
  - `reports (id PK, source_file, category, ingested_at, n_chunks)` — registre de traçabilité des documents RAG (pas de contenu métier chiffré)
- [ ] **`db/models.py`** : ORM SQLAlchemy miroir du DDL.
- [ ] Documenter dans le rapport : schéma relationnel (diagramme), clés, et la limitation `matches` vide + pourquoi.

### 3.2 Pipeline d'ingestion `load_excel_to_db.py`
- [ ] Lecture `inputs/regular NBA.xlsx` (`Données NBA`, `Equipe`) avec `pandas`/`openpyxl` (header ligne 2 pour `Données NBA`), nettoyage des colonnes 45-52 vides (`Unnamed: 45..52`) et de la colonne `datetime.time(15,0)` mal interprétée par Excel (en réalité la colonne `3PM` d'après l'ordre du dictionnaire — **à vérifier/corriger via la feuille `Dictionnaire des données`** avant insertion).
- [ ] Modèles **Pydantic** `PlayerRow`, `TeamRow` validant types et bornes (ex. `0 <= fg_pct <= 100`, `gp >= 0`) avant insertion ; rejets loggés (Logfire) avec le détail de la ligne fautive plutôt qu'un crash silencieux.
- [ ] Insertion idempotente (upsert par `(player_name, team_code, season)`), avec rapport de fin (`X joueurs insérés, Y rejetés`).

### 3.3 Tool LangChain~~~SQL → **Tool Pydantic AI** `sql_tool.py`
> Note : le brief mentionne "Tool LangChain SQL", mais cohérent avec le choix assumé d'abandonner Langchain au profit de Pydantic AI (§0.3), le tool sera implémenté **nativement en Pydantic AI** (fonction Python décorée `@agent.tool`, schéma d'entrée/sortie Pydantic) plutôt qu'avec `langchain_experimental.sql`. *(Point à confirmer avec Sarah dans le rapport — c'est un choix méthodologique assumé, à justifier explicitement, pas une déviation silencieuse du brief.)*
- [ ] Modèle Pydantic `SQLQueryRequest` (question métier) → `SQLQueryResult` (requête SQL générée, lignes résultats typées, colonnes).
- [ ] Prompt de génération NL→SQL avec **few-shot examples** couvrant les cas cités par Sarah :
  - comparaison domicile/extérieur → *exemple few-shot qui explique que cette donnée n'existe pas et route vers une réponse honnête* (plutôt que de générer une requête SQL fausse sur une table vide)
  - agrégations multicritères (ex. "top 5 joueurs par REB et AST combinés")
  - classements par équipe (`GROUP BY team_code`)
  - filtres numériques (`WHERE fg_pct > 50 AND gp > 40`)
- [ ] Exécution sécurisée : whitelist `SELECT`-only (pas d'`INSERT/UPDATE/DELETE/DROP` généré dynamiquement), requêtes paramétrées, timeout, limite de lignes.
- [ ] Validation Pydantic du résultat avant retour à l'agent (types cohérents avec le schéma `stats`).

### 3.4 Mise à jour de l'agent (`agent.py`)
- [ ] Agent Pydantic AI unique, deux tools enregistrés : `search_knowledge_base` (RAG) et `query_stats` (SQL).
- [ ] System prompt explicite sur le routage : question chiffrée/statistique → `query_stats` ; question qualitative/contextuelle → `search_knowledge_base` ; question mixte → appel des deux puis synthèse.
- [ ] `app.py` (ex-`MistralChat.py`) branché sur cet agent unique, en conservant l'UX Streamlit actuelle (historique, input chat).
- [ ] Documenter quelques **exemples de requêtes types** exécutées avec succès (capture de la requête SQL générée + résultat) dans le rapport.

---

## 4. Étape 3 — Seconde évaluation et comparatif

- [ ] Ré-exécuter `evaluate_ragas.py` sur le **même jeu de questions catégorisé** (§2.3), agent complet (RAG + SQL) → `evals/results/eval_after_sql_<date>.json`.
- [ ] **Étendre le dataset** avec des cas **mixtes texte + chiffré** (ex. "Le joueur le plus discuté dans les posts Reddit a-t-il de meilleures stats que la moyenne de son équipe ?") pour tester la combinaison des deux tools et la robustesse du routage.
- [ ] Produire le **tableau comparatif avant/après** (score moyen par catégorie, taux de réponses correctes sur les questions chiffrées réalistes, taux de détection honnête de "hors-couverture" pour domicile/extérieur et "5 derniers matchs").
- [ ] Graphiques (barres groupées avant/après par catégorie ; éventuellement radar par dimension d'évaluation) — `matplotlib`/`plotly`, exportés en image pour le rapport.
- [ ] **Analyse critique des biais et limites** (section obligatoire du brief), à couvrir explicitement :
  - mapping NL→SQL : ambiguïtés de formulation, dépendance au few-shot, risque de requêtes plausibles mais sémantiquement fausses sur `matches` (vide) ;
  - couverture des cas : données saison uniquement (pas de granularité match/domicile-extérieur) — impact direct sur les questions "signature" du brief ;
  - biais d'évaluation : LLM-judge Gemine jugé par... Gemini (juge et partie) — à signaler comme biais méthodologique connu ;
  - bruit OCR des archives Reddit (§0.2) et son effet sur le rappel RAG ;
  - couverture temporelle figée (une seule saison) limitant toute question comparative multi-saison.

---

## 5. Livrable final — Rapport de mise en place et d'évaluation du système RAG

- [ ] `reports/rapport_evaluation_rag.md`, structuré en suivant exactement les 3 étapes + synthèse :
  1. Contexte, audit de l'existant, choix techniques (reprend §0 de ce plan + justifications liées aux décisions de la mentor).
  2. Étape 1 : pipeline de données, Logfire, résultats d'évaluation baseline (tableau catégorisé).
  3. Étape 2 : schéma de base, pipeline d'ingestion, Tool SQL, exemples de requêtes.
  4. Étape 3 : comparatif avant/après (tableau + graphiques), analyse critique des biais/limites.
  5. Conclusion et axes d'extension (vraies données match-par-match, multi-saisons, multi-clubs).
- [ ] Relecture finale de cohérence avec `mission.md` (vérifier que chaque item demandé par Sarah a une section/réponse identifiable).

---

## 6. Séquencement et jalons Git (branche `develop`)

| # | Jalon | Commit suggéré |
|---|---|---|
| 1 | Setup dépendances (`pyproject.toml`), migration `utils/config.py` vers Gemini | `chore: migrate config to Gemini + add pydantic-ai/evals/logfire deps` |
| 2 | Migration `vector_store.py`/`indexer.py` vers embeddings Gemini + schémas Pydantic, régénération de l'index | `feat: migrate vector store to Gemini embeddings with Pydantic validation` |
| 3 | Intégration Logfire | `feat: instrument RAG pipeline with Logfire` |
| 4 | `evals/dataset.py`, `evals/evaluators.py`, `evaluate_ragas.py` + run baseline | `feat: add pydantic-evals based evaluation script (baseline)` |
| 5 | `db/schema.sql`, `db/models.py`, `load_excel_to_db.py` | `feat: model relational DB and Excel ingestion pipeline` |
| 6 | `sql_tool.py` + few-shot | `feat: add NL-to-SQL tool with few-shot examples` |
| 7 | `agent.py` (fusion RAG+SQL) + `app.py` | `feat: unify RAG and SQL tools into a single Pydantic AI agent` |
| 8 | Second run d'évaluation + dataset étendu (mixte) | `feat: run post-SQL evaluation and extend dataset with mixed cases` |
| 9 | Graphiques comparatifs + rapport final | `docs: write final RAG evaluation report` |

---

## 7bis. Annexe — spécification détaillée de `schemas/documents.py`

Champs calés sur les structures déjà produites par `utils/data_loader.py` et `utils/vector_store.py`, pour limiter le refactor.

```python
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from utils.config import CHUNK_SIZE


class RawDocument(BaseModel):
    """Un fichier source entier (ou une feuille Excel individuelle)."""
    source: str                                  # ex: "Reddit 1.pdf" (relatif à inputs/)
    filename: str
    full_path: Path
    category: str                                # nom du sous-dossier source ("root" si aucun) — pas d'Enum, extensible
    format: Literal["pdf", "docx", "txt", "csv", "xlsx"]
    sheet: Optional[str] = None                   # nom de la feuille si Excel multi-feuilles
    text: str = Field(..., min_length=1)
    extracted_via_ocr: bool = False               # ⚠️ nécessite de propager ce flag depuis data_loader.py

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Texte extrait vide ou ne contenant que des espaces")
        return v


class Chunk(BaseModel):
    """Un fragment issu du découpage d'un RawDocument (= chunk_dict existant)."""
    id: str                                       # format existant "{doc_index}_{chunk_index}"
    text: str = Field(..., min_length=1)
    source_document: str                          # = RawDocument.source
    category: str
    chunk_index_in_doc: int = Field(..., ge=0)     # = chunk_id_in_doc actuel
    start_char_index: int = Field(..., ge=-1)      # = start_index actuel, -1 si inconnu

    @field_validator("text")
    @classmethod
    def within_size_bounds(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Chunk vide")
        max_allowed = int(CHUNK_SIZE * 1.2)  # marge de 20%, le splitter peut légèrement dépasser
        if len(v) > max_allowed:
            raise ValueError(f"Chunk trop long ({len(v)} caractères, max {max_allowed})")
        return v


class EmbeddedChunk(BaseModel):
    """Un chunk après génération de son embedding Gemini."""
    chunk: Chunk
    embedding: list[float]
    embedding_model: str                          # ex: "text-embedding-004" — évite de comparer des vecteurs incompatibles
    dimension: int = Field(..., gt=0)

    @model_validator(mode="after")
    def dimension_matches(self) -> "EmbeddedChunk":
        if len(self.embedding) != self.dimension:
            raise ValueError(
                f"Dimension déclarée ({self.dimension}) != longueur réelle du vecteur ({len(self.embedding)})"
            )
        return self
```

> `extracted_via_ocr` implique une modification mineure de `utils/data_loader.py` : `extract_text_from_pdf` doit indiquer si le texte retourné vient du chemin standard (`PyPDF2`) ou du fallback OCR (`EasyOCR`), pour pouvoir isoler automatiquement la catégorie de test "bruitée" en §2.3.

---

## 7. Points à valider avec Sarah avant/au fil de l'implémentation
1. **SQLite vs PostgreSQL** : SQLite retenu par défaut (cohérent avec `DATABASE_URL` déjà présent dans `utils/config.py`, pas d'infra Postgres disponible) — à confirmer.
2. **Tool SQL en Pydantic AI plutôt que "Tool LangChain SQL"** littéralement — déviation assumée et documentée (cohérente avec l'abandon de Langchain décidé avec la mentor), à faire valider explicitement.
3. **Table `matches` vide** : le brief suppose implicitement des données match-par-match qui n'existent pas dans le fichier Excel fourni — à signaler tôt pour savoir si Sarah a une autre source de données, ou si on documente cela comme limite assumée.
