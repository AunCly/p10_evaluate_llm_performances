from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from database.base import Base

class Player(Base):

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    team_id: Mapped[int] = mapped_column(nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)

    def __repr__(self):
        return f"Player(id={self.id}, name='{self.name}', team_id={self.team_id}, age={self.age})"
