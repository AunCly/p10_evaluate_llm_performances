# utils/rag.py
import logging
from typing import List, Optional

from google import genai
from google.genai import types

from schemas.rag_io import RagAnswer, RetrievedContext
from utils.config import GOOGLE_API_KEY, MODEL_NAME, SEARCH_K
from utils.vector_store import VectorStoreManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SYSTEM_PROMPT_TEMPLATE = """Tu es 'NBA Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.

---
{context_str}
---

QUESTION DU FAN:
{question}

RÉPONSE DE L'ANALYSTE NBA:"""


class Rag:
    """Pipeline RAG complet : récupération de contexte (Faiss) + génération de réponse (Gemini).

    Conçu pour être instancié une seule fois (`rag = Rag()`) et réutilisé aussi bien
    par l'UI Streamlit que par un script d'évaluation.
    """

    def __init__(self, model: str = MODEL_NAME,search_k: int = SEARCH_K, system_prompt_template: str = SYSTEM_PROMPT_TEMPLATE,):

        if not GOOGLE_API_KEY:
            raise ValueError("Clé API Google manquante (GOOGLE_API_KEY).")

        self.model = model
        self.search_k = search_k
        self.system_prompt_template = system_prompt_template

        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.vector_store = VectorStoreManager()

        if self.vector_store.index is None or not self.vector_store.document_chunks:
            raise RuntimeError(
                "Index vectoriel introuvable ou vide. Exécutez 'python indexer.py' avant d'utiliser Rag()."
            )

    def _format_context(self, results: List[RetrievedContext]) -> str:
        if not results:
            return "Aucune information pertinente trouvée dans la base de connaissances pour cette question."
        return "\n\n---\n\n".join(
            f"Source: {r.source} (Score: {r.score:.1f}%)\nContenu: {r.text}"
            for r in results
        )

    def retrieve(self, question: str, k: Optional[int] = None) -> List[RetrievedContext]:
        """Recherche les chunks pertinents dans le vector store pour une question."""
        try:
            return self.vector_store.search(question, k=k or self.search_k)
        except Exception:
            logging.exception(f"Erreur pendant la recherche de contexte pour: '{question}'")
            return []

    def generate(self, question: str, context: List[RetrievedContext]) -> str:
        """Génère une réponse via Gemini à partir de la question et du contexte récupéré."""
        prompt = self.system_prompt_template.format(
            context_str=self._format_context(context), question=question
        )
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1),
            )
            if response.text:
                return response.text
            logging.warning("L'API Gemini n'a pas retourné de texte valide.")
            return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."
        except Exception:
            logging.exception("Erreur API Gemini pendant generate_content")
            return "Je suis désolé, une erreur technique m'empêche de répondre. Veuillez réessayer plus tard."

    def answer(self, question: str, k: Optional[int] = None) -> RagAnswer:
        """Exécute le pipeline RAG complet (retrieve + generate) et retourne une réponse validée."""
        context = self.retrieve(question, k=k)
        answer_text = self.generate(question, context)
        sources = sorted({c.source for c in context})
        confidence = max((c.score for c in context), default=0.0) / 100

        return RagAnswer(answer=answer_text, sources=sources, confidence=confidence)
