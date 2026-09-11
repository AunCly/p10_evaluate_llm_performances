import os
import pickle
import faiss
import numpy as np
import logging
from typing import List, Optional
from langchain_core.documents import Document
from google import genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import ValidationError

from schemas.documents import RawDocument, Chunk, EmbeddedChunk
from schemas.rag_io import RagQuery, RetrievedContext

from .config import (
    GOOGLE_API_KEY, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE,
    FAISS_INDEX_FILE, DOCUMENT_CHUNKS_FILE, CHUNK_SIZE, CHUNK_OVERLAP
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VectorStoreManager:
    """Gère la création, le chargement et la recherche dans un index Faiss."""

    def __init__(self):
        self.index: Optional[faiss.Index] = None
        self.document_chunks: List[Chunk] = []
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self._load_index_and_chunks()

    def _load_index_and_chunks(self):
        """Charge l'index Faiss et les chunks si les fichiers existent."""
        if os.path.exists(FAISS_INDEX_FILE) and os.path.exists(DOCUMENT_CHUNKS_FILE):
            try:
                logging.info(f"Chargement de l'index Faiss depuis {FAISS_INDEX_FILE}...")
                self.index = faiss.read_index(FAISS_INDEX_FILE)
                logging.info(f"Chargement des chunks depuis {DOCUMENT_CHUNKS_FILE}...")
                with open(DOCUMENT_CHUNKS_FILE, 'rb') as f:
                    self.document_chunks = pickle.load(f)
                logging.info(f"Index ({self.index.ntotal} vecteurs) et {len(self.document_chunks)} chunks chargés.")
            except Exception as e:
                logging.error(f"Erreur lors du chargement de l'index/chunks: {e}")
                self.index = None
                self.document_chunks = []
        else:
            logging.warning("Fichiers d'index Faiss ou de chunks non trouvés. L'index est vide.")

    def _split_documents_to_chunks(self, documents: List[RawDocument]) -> List[Chunk]:
        """Découpe les documents en chunks validés (Pydantic) avec métadonnées."""
        logging.info(f"Découpage de {len(documents)} documents en chunks (taille={CHUNK_SIZE}, chevauchement={CHUNK_OVERLAP})...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len, # Important: mesure en caractères
            add_start_index=True, # Ajoute la position de début du chunk dans le document original
        )

        all_chunks: List[Chunk] = []
        doc_counter = 0
        for doc in documents:
            # Convertit notre format de document en format Langchain Document pour le splitter
            langchain_doc = Document(page_content=doc.text)
            langchain_chunks = text_splitter.split_documents([langchain_doc])
            logging.info(f"Document '{doc.source}' découpé en {len(langchain_chunks)} chunks.")

            # Valide chaque chunk via Pydantic avant de le retenir ; les chunks
            # invalides (vides, trop longs...) sont rejetés et journalisés plutôt
            # que de faire crasher tout le découpage.
            for i, lc_chunk in enumerate(langchain_chunks):
                try:
                    chunk = Chunk(
                        id=f"{doc_counter}_{i}",
                        text=lc_chunk.page_content,
                        source_document=doc.source,
                        category=doc.category,
                        chunk_index_in_doc=i,
                        start_char_index=lc_chunk.metadata.get("start_index", -1),
                        extracted_via_ocr=doc.extracted_via_ocr,
                    )
                except ValidationError as e:
                    logging.error(f"Chunk rejeté ({doc_counter}_{i}, source='{doc.source}'): {e}")
                    continue
                all_chunks.append(chunk)
            doc_counter += 1

        logging.info(f"Total de {len(all_chunks)} chunks valides créés.")
        return all_chunks

    def _generate_embeddings(self, chunks: List[Chunk]) -> tuple[List[Chunk], Optional[np.ndarray]]:
        """Génère les embeddings pour une liste de chunks via l'API Google.

        Chaque embedding est validé (dimension cohérente) via `EmbeddedChunk`
        avant d'être retenu. Un chunk dont l'appel d'embedding échoue ou dont
        l'embedding est invalide est rejeté et journalisé (pas de vecteur nul
        silencieux qui fausserait la recherche).

        Retourne les chunks effectivement embeddés (dans le même ordre que
        leurs embeddings) et la matrice d'embeddings correspondante.
        """
        if not GOOGLE_API_KEY:
            logging.error("Impossible de générer les embeddings: GOOGLE_API_KEY manquante.")
            return [], None
        if not chunks:
            logging.warning("Aucun chunk fourni pour générer les embeddings.")
            return [], None

        logging.info(f"Génération des embeddings pour {len(chunks)} chunks (modèle: {EMBEDDING_MODEL})...")
        valid_chunks: List[Chunk] = []
        valid_embeddings: List[List[float]] = []
        total_batches = (len(chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

        for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch_num = (i // EMBEDDING_BATCH_SIZE) + 1
            batch_chunks = chunks[i:i + EMBEDDING_BATCH_SIZE]
            texts_to_embed = [chunk.text for chunk in batch_chunks]

            logging.info(f"  Traitement du lot {batch_num}/{total_batches} ({len(texts_to_embed)} chunks)")
            try:
                response = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=texts_to_embed
                )
                batch_embeddings = [embedding.values for embedding in response.embeddings]
            except Exception as e:
                logging.error(
                    f"Lot {batch_num} rejeté ({len(texts_to_embed)} chunks): échec de l'appel d'embedding ({e})."
                )
                continue

            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                try:
                    EmbeddedChunk(
                        chunk=chunk,
                        embedding=embedding,
                        embedding_model=EMBEDDING_MODEL,
                        dimension=len(embedding),
                    )
                except ValidationError as e:
                    logging.error(f"Embedding rejeté pour le chunk '{chunk.id}': {e}")
                    continue
                valid_chunks.append(chunk)
                valid_embeddings.append(embedding)

        if not valid_embeddings:
            logging.error("Aucun embedding valide n'a pu être généré.")
            return [], None

        embeddings_array = np.array(valid_embeddings).astype('float32')
        logging.info(
            f"Embeddings générés avec succès pour {len(valid_chunks)}/{len(chunks)} chunks. Shape: {embeddings_array.shape}"
        )
        return valid_chunks, embeddings_array

    def build_index(self, documents: List[RawDocument]):
        """Construit l'index Faiss à partir des documents."""
        if not documents:
            logging.warning("Aucun document fourni pour construire l'index.")
            return

        # 1. Découper en chunks valides
        chunks = self._split_documents_to_chunks(documents)
        if not chunks:
            logging.error("Le découpage n'a produit aucun chunk valide. Impossible de construire l'index.")
            return

        # 2. Générer les embeddings (avec rejet journalisé des échecs)
        valid_chunks, embeddings = self._generate_embeddings(chunks)
        if embeddings is None or not valid_chunks:
            logging.error("Aucun embedding valide n'a été généré. Construction de l'index annulée.")
            self.document_chunks = []
            self.index = None
            # Supprimer les fichiers potentiellement corrompus
            if os.path.exists(FAISS_INDEX_FILE): os.remove(FAISS_INDEX_FILE)
            if os.path.exists(DOCUMENT_CHUNKS_FILE): os.remove(DOCUMENT_CHUNKS_FILE)
            return

        self.document_chunks = valid_chunks

        # 3. Créer l'index Faiss optimisé pour la similarité cosinus
        dimension = embeddings.shape[1]
        logging.info(f"Création de l'index Faiss optimisé pour la similarité cosinus avec dimension {dimension}...")

        # Normaliser les embeddings pour la similarité cosinus
        faiss.normalize_L2(embeddings)

        # Créer un index pour la similarité cosinus (IndexFlatIP = produit scalaire)
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        logging.info(f"Index Faiss créé avec {self.index.ntotal} vecteurs.")

        # 4. Sauvegarder l'index et les chunks
        self._save_index_and_chunks()

    def _save_index_and_chunks(self):
        """Sauvegarde l'index Faiss et la liste des chunks."""
        if self.index is None or not self.document_chunks:
            logging.warning("Tentative de sauvegarde d'un index ou de chunks vides.")
            return

        os.makedirs(os.path.dirname(FAISS_INDEX_FILE), exist_ok=True)
        os.makedirs(os.path.dirname(DOCUMENT_CHUNKS_FILE), exist_ok=True)

        try:
            logging.info(f"Sauvegarde de l'index Faiss dans {FAISS_INDEX_FILE}...")
            faiss.write_index(self.index, FAISS_INDEX_FILE)
            logging.info(f"Sauvegarde des chunks dans {DOCUMENT_CHUNKS_FILE}...")
            with open(DOCUMENT_CHUNKS_FILE, 'wb') as f:
                pickle.dump(self.document_chunks, f)
            logging.info("Index et chunks sauvegardés avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors de la sauvegarde de l'index/chunks: {e}")

    def search(self, query_text: str, k: int = 5, min_score: Optional[float] = None) -> List[RetrievedContext]:
        """
        Recherche les k chunks les plus pertinents pour une requête.

        Args:
            query_text: Texte de la requête
            k: Nombre de résultats à retourner
            min_score: Score minimum (entre 0 et 1) pour inclure un résultat

        Returns:
            Liste de `RetrievedContext` validés (texte non vide, score dans [0,100],
            source renseignée) prêts à être remontés à l'agent.
        """
        if self.index is None or not self.document_chunks:
            logging.warning("Recherche impossible: l'index Faiss n'est pas chargé ou est vide.")
            return []
        if not GOOGLE_API_KEY:
            logging.error("Recherche impossible: GOOGLE_API_KEY manquante pour générer l'embedding de la requête.")
            return []

        try:
            query = RagQuery(question=query_text)
        except ValidationError as e:
            logging.error(f"Requête de recherche rejetée (invalide): {e}")
            return []

        logging.info(f"Recherche des {k} chunks les plus pertinents pour: '{query.question}'")
        try:
            # 1. Générer l'embedding de la requête
            response = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=[query.question],
            )
            query_embedding = np.array([response.embeddings[0].values]).astype('float32')

            # Normaliser l'embedding de la requête pour la similarité cosinus
            faiss.normalize_L2(query_embedding)

            # 2. Rechercher dans l'index Faiss
            # Pour IndexFlatIP: scores = produit scalaire (plus grand = meilleur)
            # indices: index des chunks correspondants dans self.document_chunks
            # Demander plus de résultats si un score minimum est spécifié
            search_k = k * 3 if min_score is not None else k
            scores, indices = self.index.search(query_embedding, search_k)

            # 3. Formater et valider les résultats
            results: List[RetrievedContext] = []
            if indices.size > 0: # Vérifier s'il y a des résultats
                for i, idx in enumerate(indices[0]):
                    if not (0 <= idx < len(self.document_chunks)): # Vérifier la validité de l'index
                        logging.warning(f"Index Faiss {idx} hors limites (taille des chunks: {len(self.document_chunks)}).")
                        continue

                    chunk = self.document_chunks[idx]
                    # Pour IndexFlatIP avec vecteurs normalisés, le score brut est entre -1 et 1.
                    # On le convertit en pourcentage (0-100%), borné pour rester dans les
                    # contraintes du schéma RetrievedContext.
                    raw_score = float(scores[0][i])
                    similarity = max(0.0, min(100.0, raw_score * 100))

                    # Filtrer les résultats en fonction du score minimum
                    # Le min_score est entre 0 et 1, mais similarity est en pourcentage (0-100)
                    min_score_percent = min_score * 100 if min_score is not None else 0
                    if min_score is not None and similarity < min_score_percent:
                        logging.debug(f"Document filtré (score {similarity:.2f}% < minimum {min_score_percent:.2f}%)")
                        continue

                    try:
                        context = RetrievedContext(
                            text=chunk.text,
                            score=similarity,
                            source=chunk.source_document,
                            chunk_id=chunk.id,
                        )
                    except ValidationError as e:
                        logging.error(f"Résultat de recherche rejeté pour le chunk '{chunk.id}': {e}")
                        continue

                    results.append(context)

            # Trier par score (similarité la plus élevée en premier)
            results.sort(key=lambda r: r.score, reverse=True)

            # Limiter au nombre demandé (k) si nécessaire
            if len(results) > k:
                results = results[:k]

            if min_score is not None:
                min_score_percent = min_score * 100
                logging.info(f"{len(results)} chunks pertinents trouvés (score minimum: {min_score_percent:.2f}%).")
            else:
                logging.info(f"{len(results)} chunks pertinents trouvés.")

            return results
        except Exception as e:
            logging.error(f"Erreur inattendue lors de la recherche: {e}")
            return []
