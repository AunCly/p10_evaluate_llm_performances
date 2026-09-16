CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team_id INT REFERENCES teams(id),
    age INT
);

CREATE TABLE stats (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES players(id),
    gp INT,
    w INT,
    l INT,
    min FLOAT,
    pts FLOAT,
    fgm FLOAT,
    fga FLOAT,
    fg_pct FLOAT,
    three_p_pm FLOAT,
    three_p_pa FLOAT,
    three_p_pct FLOAT,
    ftm FLOAT,
    fta FLOAT,
    ft_pct FLOAT,
    oreb FLOAT,
    dreb FLOAT,
    reb FLOAT,
    ast FLOAT,
    tov FLOAT,
    stl FLOAT,
    blk FLOAT,
    pf FLOAT,
    fp FLOAT,
    dd2 INT,
    td3 INT,
    plus_minus FLOAT,
    offrtg FLOAT,
    defrtg FLOAT,
    netrtg FLOAT,
    ast_pct FLOAT,
    ast_to FLOAT,
    ast_ratio FLOAT,
    oreb_pct FLOAT,
    dreb_pct FLOAT,
    reb_pct FLOAT,
    to_ratio FLOAT,
    efg_pct FLOAT,
    ts_pct FLOAT,
    usg_pct FLOAT,
    pace FLOAT,
    pie FLOAT,
    poss FLOAT
);

CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    season VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    home_team_id INT REFERENCES teams(id),
    away_team_id INT REFERENCES teams(id),
    home_score INT,
    away_score INT
);

CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    n_chunks INT
);