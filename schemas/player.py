from pydantic import BaseModel

class Player(BaseModel):
    name: str
    team_id: int
    age: int