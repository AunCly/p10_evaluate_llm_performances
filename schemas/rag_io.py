from typing import List

from pydantic import BaseModel, Field, field_validator


class RagQuery(BaseModel):
    """Question utilisateur validée avant d'être transmise au pipeline RAG."""
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La question ne peut pas être vide ou ne contenir que des espaces")
        return v.strip()


class RetrievedContext(BaseModel):
    """Un résultat de recherche vectorielle, validé avant d'être remonté à l'agent."""
    text: str = Field(..., min_length=1)
    score: float = Field(..., ge=0, le=100)         # similarité cosinus en pourcentage
    source: str = Field(..., min_length=1)          # document/chunk d'origine
    chunk_id: str

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le texte du contexte récupéré ne peut pas être vide")
        return v


class SqlQueryResult(BaseModel):
    """Résultat d'une requête SQL exécutée par l'agent (stats joueur ou requête libre)."""
    query: str = Field(..., min_length=1)
    result: str = Field(..., min_length=1)


class RagAnswer(BaseModel):
    """Réponse produite par le tool RAG, avec ses sources et sa confiance."""
    answer: str = Field(..., min_length=1)
    retrieved_contexts: List[RetrievedContext] = Field(default_factory=list)
    sql_results: List[SqlQueryResult] = Field(default_factory=list)
    #confidence: float = Field(..., ge=0, le=1)
