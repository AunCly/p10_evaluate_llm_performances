from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from database.player import Player

from database.stats import Stats
from database.team import Team
from schemas.row import Row


def column_mapping(df: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "Player" : "name",
        "Team": "team_name",
        "Age": "age",
        "GP": "gp",
        "W": "w",
        "L": "l",
        "Min": "min",
        "PTS": "pts",
        "FGM": "fgm",
        "FGA": "fga",
        "FG%": "fg_pct",
        "3PM": "three_p_pm",
        "3PA": "three_p_pa",
        "3P%": "three_p_pct",
        "FTM": "ftm",
        "FTA": "fta",
        "FT%": "ft_pct",
        "OREB": "oreb",
        "DREB": "dreb",
        "REB": "reb",
        "AST": "ast",
        "TOV": "tov",
        "STL": "stl",
        "BLK": "blk",
        "PF": "pf",
        "FP": "fp",
        "DD2": "dd2",
        "TD3": "td3",
        "+/-": "plus_minus",
        "OFFRTG": "offrtg",
        "DEFRTG": "defrtg",
        "NETRTG": "netrtg",
        "AST%": "ast_pct",
        "AST/TO": "ast_to",
        "AST RATIO": "ast_ratio",
        "OREB%": "oreb_pct",
        "DREB%": "dreb_pct",
        "REB%": "reb_pct",
        "TO RATIO": "to_ratio",
        "EFG%": "efg_pct",
        "TS%": "ts_pct",
        "USG%": "usg_pct",
        "PACE": "pace",
        "PIE": "pie",
        "POSS": "poss"
    }

    col_name = df.columns[11]
    df.rename(columns={col_name: "3PM"}, inplace=True)

    df.rename(columns=columns, inplace=True)

    return df

def load_excel_to_db(filename: str) -> None:
    try:
        base_path = Path(__file__).parent.parent
        db_path = base_path / "database" / "database.sqlite"

        engine = create_engine(f"sqlite:///{db_path.resolve()}")
        excel_file_path = base_path / "inputs" / filename

        with open(excel_file_path, 'rb') as f:
            df = pd.read_excel(f, header=1)
            df = column_mapping(df)

            with Session(engine) as session:
                for index, pandas_row in df.iterrows():

                    row_dict = pandas_row.to_dict()

                    # 2. Validation Pydantic
                    try:
                        validated_row = Row(**row_dict)
                    except Exception as e:
                        print(f"Error processing row {index}: {e}")
                        continue

                    team_name = validated_row.team_name
                    stmt = select(Team).where(Team.name == team_name)
                    team = session.scalars(stmt).one_or_none()

                    if not team:
                        team = Team(name=team_name)
                        session.add(team)
                        session.flush()

                    player_name = validated_row.name

                    stmt = select(Player).where(Player.name == player_name)
                    player = session.scalars(stmt).one_or_none()

                    if not player:
                        player = Player(
                            name=player_name,
                            team_id=team.id,
                            age=validated_row.age
                        )
                        session.add(player)
                        session.flush()

                    stat = Stats(
                        player_id=player.id,
                        gp=validated_row.gp,
                        w=validated_row.w,
                        l=validated_row.l,
                        min=validated_row.min,
                        pts=validated_row.pts,
                        fgm=validated_row.fgm,
                        fga=validated_row.fga,
                        fg_pct=validated_row.fg_pct,
                        three_p_pm=validated_row.three_p_pm,
                        three_p_pa=validated_row.three_p_pa,
                        three_p_pct=validated_row.three_p_pct,
                        ftm=validated_row.ftm,
                        fta=validated_row.fta,
                        ft_pct=validated_row.ft_pct,
                        oreb=validated_row.oreb,
                        dreb=validated_row.dreb,
                        reb=validated_row.reb,
                        ast=validated_row.ast,
                        tov=validated_row.tov,
                        stl=validated_row.stl,
                        blk=validated_row.blk,
                        pf=validated_row.pf,
                        fp=validated_row.fp,
                        dd2=validated_row.dd2,
                        td3=validated_row.td3,
                        plus_minus=validated_row.plus_minus,
                        offrtg=validated_row.offrtg,
                        defrtg=validated_row.defrtg,
                        netrtg=validated_row.netrtg,
                        ast_pct=validated_row.ast_pct,
                        ast_to=validated_row.ast_to,
                        ast_ratio=validated_row.ast_ratio,
                        oreb_pct=validated_row.oreb_pct,
                        dreb_pct=validated_row.dreb_pct,
                        reb_pct=validated_row.reb_pct,
                        to_ratio=validated_row.to_ratio,
                        efg_pct=validated_row.efg_pct,
                        ts_pct=validated_row.ts_pct,
                        usg_pct=validated_row.usg_pct,
                        pace=validated_row.pace,
                        pie=validated_row.pie,
                        poss=validated_row.poss
                    )
                    session.add(stat)

                session.commit()
                print("Données importées avec succès !")

    except Exception as e:
        print("An error occurred while loading the Excel file into the database:")
        print(e)


if __name__ == "__main__":
    load_excel_to_db('regular_NBA.xlsx')