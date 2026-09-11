from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from utils.config import CHUNK_SIZE


class RawDocument(BaseModel):
    """Un fichier source entier (ou une feuille Excel individuelle)."""
    source: str                                   # ex: "Reddit 1.pdf" (relatif à inputs/)
    filename: str
    full_path: Path
    category: str                                 # nom du sous-dossier source ("root" si aucun)
    format: Literal["pdf", "docx", "txt", "csv", "xlsx"]
    sheet: Optional[str] = None                   # nom de la feuille si Excel multi-feuilles
    text: str = Field(..., min_length=1)
    extracted_via_ocr: bool = False                # texte issu du fallback OCR (PDF scanné)

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Texte extrait vide ou ne contenant que des espaces")
        return v


class Chunk(BaseModel):
    """Un fragment issu du découpage d'un RawDocument."""
    id: str                                        # format "{doc_index}_{chunk_index}"
    text: str = Field(..., min_length=1)
    source_document: str                           # = RawDocument.source
    category: str                                  # = RawDocument.category
    chunk_index_in_doc: int = Field(..., ge=0)
    start_char_index: int = Field(..., ge=-1)       # -1 si inconnu
    extracted_via_ocr: bool = False                 # propagé depuis le RawDocument d'origine

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
    embedding_model: str                           # ex: "gemini-embedding-001"
    dimension: int = Field(..., gt=0)

    @model_validator(mode="after")
    def dimension_matches(self) -> "EmbeddedChunk":
        if len(self.embedding) != self.dimension:
            raise ValueError(
                f"Dimension déclarée ({self.dimension}) != longueur réelle du vecteur ({len(self.embedding)})"
            )
        return self
