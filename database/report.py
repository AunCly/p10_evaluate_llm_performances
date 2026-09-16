from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class Report(DeclarativeBase):
    __tablename__ = "report"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_file: Mapped[str]
    category: Mapped[str]
    ingested_at: Mapped[str]
    n_chunks: Mapped[int]
