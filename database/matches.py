from sqlalchemy.orm import DeclarativeBase

class Match(DeclarativeBase):

    __tablename__ = "matches"

    id: int
    season: str
    date: str
    home_team_code: str
    away_team_code: str
    home_score: int
    away_score: int

