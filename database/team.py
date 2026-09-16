from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from database.base import Base

class Team(Base):

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)

    def __repr__(self):
        return f"Team(id={self.id}, name='{self.name}')"
