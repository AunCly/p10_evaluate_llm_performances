from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from database.base import Base


class Stats(Base):

    __tablename__ = "stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    gp: Mapped[int]
    w: Mapped[int]
    l: Mapped[int]
    min: Mapped[float]
    pts: Mapped[float]
    fgm: Mapped[float]
    fga: Mapped[float]
    fg_pct: Mapped[float]
    three_p_pm: Mapped[float]
    three_p_pa: Mapped[float]
    three_p_pct: Mapped[float]
    ftm: Mapped[float]
    fta: Mapped[float]
    ft_pct: Mapped[float]
    oreb: Mapped[float]
    dreb: Mapped[float]
    reb: Mapped[float]
    ast: Mapped[float]
    tov: Mapped[float]
    stl: Mapped[float]
    blk: Mapped[float]
    pf: Mapped[float]
    fp: Mapped[float]
    dd2: Mapped[int]
    td3: Mapped[int]
    plus_minus: Mapped[float]
    offrtg: Mapped[float]
    defrtg: Mapped[float]
    netrtg: Mapped[float]
    ast_pct: Mapped[float]
    ast_to: Mapped[float]
    ast_ratio: Mapped[float]
    oreb_pct: Mapped[float]
    dreb_pct: Mapped[float]
    reb_pct: Mapped[float]
    to_ratio: Mapped[float]
    efg_pct: Mapped[float]
    ts_pct: Mapped[float]
    usg_pct: Mapped[float]
    pace: Mapped[float]
    pie: Mapped[float]
    poss: Mapped[float]