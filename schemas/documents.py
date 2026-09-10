from pathlib import Path
from pydantic import BaseModel, Field

class RawDocument(BaseModel):
    """Un fichier source entier (ou une feuille Excel individuelle)."""
    source: str
    filename: str
    full_path: Path
    text: str

class Chunk(BaseModel):
    """Un fragment issu du découpage d'un RawDocument (= chunk_dict existant)."""
    id: str
    text: str = Field(..., min_length=1)
    source_document: str
    metadadas: dict
    chunk_index_in_doc: int = Field(..., ge=0)
    start_char_index: int = Field(..., ge=-1)