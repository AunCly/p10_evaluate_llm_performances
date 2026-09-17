import logging
from pathlib import Path
from typing import List, Optional

from google import genai
from pydantic_ai import RunContext, Agent, Tool
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from schemas.rag_io import RagAnswer, RetrievedContext
from utils.config import GOOGLE_API_KEY, MODEL_NAME, SEARCH_K
from utils.vector_store import VectorStoreManager
import logfire

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SYSTEM_PROMPT_TEMPLATE = """
Tu es 'NBA Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.
Si la question ne peut pas être répondue avec les informations fournies, réponds honnêtement que tu ne sais pas.
Tu disposes d'un contexte récupéré depuis une base de connaissances NBA, que tu dois utiliser pour formuler ta réponse. Ne fais pas de suppositions ou d'inventions.
Si le contexte ne contient pas d'informations pertinentes, indique clairement que tu ne peux pas répondre à la question.
Tu dispose d'une base de données SQLite avec les statistiques des joueurs, que tu peux interroger via la fonction get_stats(player_name).
Tu peux également effectuer une recherche dans la base de connaissances via la fonction index_search(query) pour récupérer des extraits pertinents.

Lexique de NBA:
### Statistiques Générales et de Base
* **gp** (*Games Played*) : Nombre de matchs joués.
* **w** (*Wins*) : Nombre de victoires.
* **l** (*Losses*) : Nombre de défaites.
* **min** (*Minutes*) : Minutes jouées en moyenne par match.
* **pts** (*Points*) : Points marqués par match.
* **fgm** (*Field Goals Made*) : Paniers réussis (à 2 et 3 points) par match.
* **fga** (*Field Goals Attempted*) : Tirs tentés par match.
* **fg_pct** (*Field Goal Percentage*) : Pourcentage de réussite aux tirs.
* **three_p_pm** (*3-Point Field Goals Made*) : Paniers à 3 points réussis par match.
* **three_p_pa** (*3-Point Field Goals Attempted*) : Tirs à 3 points tentés par match.
* **three_p_pct** (*3-Point Field Goal Percentage*) : Pourcentage de réussite à 3 points.
* **ftm** (*Free Throws Made*) : Lancers francs réussis par match.
* **fta** (*Free Throws Attempted*) : Lancers francs tentés par match.
* **ft_pct** (*Free Throw Percentage*) : Pourcentage de réussite aux lancers francs.

### Rebonds, Passes, et Défense
* **oreb** (*Offensive Rebounds*) : Rebonds offensifs par match.
* **dreb** (*Defensive Rebounds*) : Rebonds défensifs par match.
* **reb** (*Rebounds*) : Total des rebonds par match (offensifs + défensifs).
* **ast** (*Assists*) : Passes décisives par match.
* **tov** (*Turnovers*) : Ballons perdus par match.
* **stl** (*Steals*) : Interceptions par match.
* **blk** (*Blocks*) : Contres par match.
* **pf** (*Personal Fouls*) : Fautes personnelles par match.

### Accomplissements et Statistiques Avancées
* **fp** (*Fantasy Points*) : Points générés pour les ligues Fantasy.
* **dd2** (*Double-Doubles*) : Nombre de matchs avec au moins 10 unités dans deux catégories statistiques (ex. points et rebonds).
* **td3** (*Triple-Doubles*) : Nombre de matchs avec au moins 10 unités dans trois catégories statistiques.
* **plus_minus** (*Plus-Minus*) : Différentiel de points de l'équipe (+ ou -) lorsque le joueur est sur le terrain.
* **offrtg** (*Offensive Rating*) : Points marqués par l'équipe pour 100 possessions quand le joueur est sur le terrain.
* **defrtg** (*Defensive Rating*) : Points encaissés par l'équipe pour 100 possessions quand le joueur est sur le terrain.
* **netrtg** (*Net Rating*) : Différence entre l'Offensive Rating et le Defensive Rating.

### Ratios et Pourcentages Avancés
* **ast_pct** (*Assist Percentage*) : Pourcentage des paniers de l'équipe réussis grâce à une passe du joueur lorsqu'il est en jeu.
* **ast_to** (*Assist to Turnover Ratio*) : Rapport entre les passes décisives et les ballons perdus.
* **ast_ratio** (*Assist Ratio*) : Passes décisives pour 100 possessions.
* **oreb_pct** (*Offensive Rebound Percentage*) : Pourcentage des rebonds offensifs disponibles capturés par le joueur.
* **dreb_pct** (*Defensive Rebound Percentage*) : Pourcentage des rebonds défensifs disponibles capturés par le joueur.
* **reb_pct** (*Rebound Percentage*) : Pourcentage total des rebonds capturés par le joueur.
* **to_ratio** (*Turnover Ratio*) : Ballons perdus pour 100 possessions.
* **efg_pct** (*Effective Field Goal Percentage*) : Pourcentage de tirs effectif (ajusté pour valoriser la valeur supérieure des tirs à 3 points).
* **ts_pct** (*True Shooting Percentage*) : Efficacité globale au tir prenant en compte les tirs à 2 pts, 3 pts et lancers francs.
* **usg_pct** (*Usage Percentage*) : Pourcentage des actions de l'équipe conclues par le joueur (tir, lancer franc ou perte de balle) pendant son temps de jeu.
* **pace** (*Pace*) : Rythme de jeu (nombre de possessions estimé pour 48 minutes).
* **pie** (*Player Impact Estimate*) : Mesure globale de l'impact et de la contribution statistique d'un joueur par rapport au match.
* **poss** (*Possessions*) : Nombre total de possessions jouées.
"""

class Rag:
    """Pipeline RAG complet : récupération de contexte (Faiss) + génération de réponse (Gemini).

    Conçu pour être instancié une seule fois (`rag = Rag()`) et réutilisé aussi bien
    par l'UI Streamlit que par un script d'évaluation.
    """

    def __init__(self, model: str = MODEL_NAME, search_k: int = SEARCH_K, system_prompt_template: str = SYSTEM_PROMPT_TEMPLATE,):

        logfire.info('Instanciation du Rag !')

        if not GOOGLE_API_KEY:
            raise ValueError("Clé API Google manquante (GOOGLE_API_KEY).")

        self.search_k = search_k
        self.system_prompt_template = system_prompt_template
        self.agent = Agent(
            model=MODEL_NAME,
            system_prompt=system_prompt_template,
            tools=[
                Tool(self.get_stats, takes_ctx=True),
                Tool(self.index_search, takes_ctx=True)
            ]
        )
        self.vector_store = VectorStoreManager()

        if self.vector_store.index is None or not self.vector_store.document_chunks:
            raise RuntimeError(
                "Index vectoriel introuvable ou vide. Exécutez 'python indexer.py' avant d'utiliser Rag()."
            )

    def get_stats(self, ctx: RunContext[str], player_name: str) -> str:
        """Retourne les statistiques d'un joueur depuis la base de données SQLite."""
        logfire.info('Utilisation de get_stats pour le joueur : {player_name}', player_name=player_name)

        base_path = Path(__file__).parent.parent
        db_path = base_path / "database" / "database.sqlite"
        engine = create_engine(f"sqlite:///{db_path.resolve()}")

        with Session(engine) as session:
            logfire.info(f'SELECT * FROM stats INNER JOIN players ON stats.player_id = players.id WHERE players.name = {player_name}')

            stmt = text("SELECT * FROM stats INNER JOIN players ON stats.player_id = players.id WHERE players.name = :player_name")
            result = session.execute(stmt, {"player_name": player_name}).mappings().fetchall()

        logfire.info('Résultat de la requête pour le joueur {player_name} : {result}', player_name=player_name, result=result)

        return str([dict(r) for r in result]) if result else f"Aucune statistique trouvée pour le joueur '{player_name}'."

    def index_search(self, ctx: RunContext[str], query: str) -> List[RetrievedContext]:
        """Recherche des extraits qualitatifs/textuels dans la base de connaissance"""
        logfire.info('Recherche de contexte pour la question : {question}', question=query)

        try:
            return self.vector_store.search(query, k=5)
        except Exception:
            logging.exception(f"Erreur pendant la recherche de contexte pour: '{query}'")
            return []

    def _format_context(self, results: List[RetrievedContext]) -> str:
        if not results:
            return "Aucune information pertinente trouvée dans la base de connaissances pour cette question."
        return "\n\n---\n\n".join(
            f"Source: {r.source} (Score: {r.score:.1f}%)\nContenu: {r.text}"
            for r in results
        )

    def generate(self, question: str) -> str:
        """Génère une réponse via Gemini à partir de la question et du contexte récupéré."""
        try:

            logfire.info('Prompt final : {prompt}', prompt=question)

            response = self.agent.run_sync(question)

            if response:
                return response.output
            logging.warning("L'API Gemini n'a pas retourné de texte valide.")
            return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."
        except Exception:
            logging.exception("Erreur API Gemini pendant generate_content")
            return "Je suis désolé, une erreur technique m'empêche de répondre. Veuillez réessayer plus tard."

    def answer(self, question: str, k: Optional[int] = None) -> RagAnswer:
        """Exécute le pipeline RAG complet (retrieve + generate) et retourne une réponse validée."""

        logfire.info('Pipeline RAG exécuté pour la question : {question}', question=question)

        answer_text = self.generate(question)
        #sources = sorted({c.source for c in context})
       #confidence = max((c.score for c in context), default=0.0) / 100

        logfire.info('Answer : {answer}', answer=answer_text)

        return RagAnswer(answer=answer_text)
