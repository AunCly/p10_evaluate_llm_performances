from dataclasses import dataclass

import logfire
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from schemas.rag_io import RagAnswer
from utils.rag import Rag


@dataclass
class RagInputs:
    question: str


eval_cases = [
    # ---------------------------------------------------------
    # CAS STANDARDS (Extraction directe d'informations)
    # ---------------------------------------------------------
    Case(
        inputs=RagInputs(
            question="Selon les documents, qui est la première option offensive la plus efficace de l'histoire des playoffs NBA ?",
        ),
        expected_output="Selon le post Reddit, c'est Reggie Miller. Kawhi Leonard est le seul joueur qui s'en approche.",
    ),
    Case(
        inputs=RagInputs(
            question="Combien de fois Reggie Miller a-t-il été sélectionné au All-Star Game et pourquoi un utilisateur trouve-t-il cela étonnant ?",
        ),
        expected_output="Reggie Miller a été sélectionné 5 fois. L'utilisateur trouve cela étonnant (wild) car c'est moins que des joueurs comme Kyle Lowry ou Joe Johnson.",
    ),
    Case(
        inputs=RagInputs(
            question="Quel joueur a vu son niveau d'énergie chuter ('run out of gas') face au jeu très physique ('bully ball') de Julius Randle ?",
        ),
        expected_output="LeBron James a été épuisé par le jeu physique de Julius Randle.",
    ),
    Case(
        inputs=RagInputs(
            question="Pourquoi SGA (Shai Gilgeous-Alexander) est-il fortement critiqué dans les commentaires, bien qu'il soit considéré comme un joueur du top 3-5 ?",
        ),
        expected_output="SGA est critiqué pour son 'foul baiting' (provocation de fautes), ses flops exagérés (flailing) et le fait de manipuler le système d'arbitrage au lieu de jouer de manière 'honorable'.",
    ),

    # ---------------------------------------------------------
    # CAS PIÈGES (Fausse prémisse / Illusion / Hallucination)
    # ---------------------------------------------------------
    # [PIÈGE]
    Case(
        inputs=RagInputs(
            question="Quelle équipe NBA a réussi à atteindre les Finales sans l'avantage du terrain lors des 3 premiers tours, pour ensuite avoir l'avantage du terrain lors de la grande Finale face aux Panthers ?",
        ),
        expected_output="C'est une question piège. Aucune équipe de la NBA n'a accompli cela (la réponse dans le thread NBA précise 'none'). L'événement mentionné concerne les Oilers d'Edmonton, qui sont une équipe de NHL (hockey sur glace) et non de NBA, et qui ont effectivement joué les Panthers en finale NHL.",
    ),
    # [PIÈGE]
    Case(
        inputs=RagInputs(
            question="Lors de quelles finales NBA les Edmonton Oilers ont-ils joué ?",
        ),
        expected_output="Les Edmonton Oilers n'ont jamais joué de finales NBA car c'est une franchise de NHL (hockey sur glace). Le document compare simplement le parcours des Oilers en NHL avec la situation en NBA.",
    ),
    # [PIÈGE]
    Case(
        inputs=RagInputs(
            question="D'après l'utilisateur 'chunksss', combien de fois Reggie Miller a-t-il été dans le top 10 des passes décisives en playoffs ?",
        ),
        expected_output="Le document indique que Reggie Miller a été dans le top 10 des passes décisives 3 fois dans sa carrière, mais cela concerne la saison régulière ou le classement général, la citation exacte de chunksss dit 'Hell, he was only ever even top 10 in assists 3 times', sans spécifier explicitement les playoffs pour cette statistique particulière.",
    ),
    # [PIÈGE]
    Case(
        inputs=RagInputs(
            question="Quel joueur des Dallas Mavericks a été drafté grâce à la stratégie de tanking de l'équipe pour rater les playoffs de la NHL ?",
        ),
        expected_output="Les Mavericks ont effectivement tanké pour éviter le play-in et conserver leur choix pour drafter Dereck Lively II. Cependant, ils jouent en NBA et non en NHL (la NHL est mentionnée dans un autre contexte).",
    ),

    # ---------------------------------------------------------
    # CAS COMPLEXES (Synthèse et Raisonnement)
    # ---------------------------------------------------------
    Case(
        inputs=RagInputs(
            question="Pourquoi, selon les fans sur Reddit, les médias NBA ont-ils du mal à marketer une potentielle Finale entre les deux meilleures équipes statistiques ?",
        ),
        expected_output="Les fans expliquent que la NBA et ses médias sont obsédés par les superstars, les gros marchés et les intrigues (drama/tabloid) plutôt que par le beau jeu d'équipe. Une finale avec un 'MVP ennuyeux' ou sans superstar ultra-médiatique (comme LeBron) est difficile à vendre pour des médias en quête d'engagement algorithmique.",
    ),
    Case(
        inputs=RagInputs(
            question="Explique en quoi la façon de défendre de Julius Randle l'a avantagé par rapport à Karl-Anthony Towns (KAT) lors des playoffs.",
        ),
        expected_output="Selon l'utilisateur Gbaby245, Julius Randle défend avec son torse (chest) et non avec ses mains, ce qui lui évite de commettre les fautes que KAT a tendance à faire. De plus, sa puissance physique empêche des joueurs comme Luka et LeBron de le repousser lors des drives.",
    ),

# ---------------------------------------------------------
    # CAS STANDARDS (Bon déclenchement du tool et extraction basique)
    # ---------------------------------------------------------
    Case(
        inputs=RagInputs(
            question="Combien de points totaux (PTS) Shai Gilgeous-Alexander a-t-il marqués cette saison ?",
        ),
        expected_output="Le tool SQL doit être appelé. Shai Gilgeous-Alexander a marqué 2485 points (PTS).",
    ),
    Case(
        inputs=RagInputs(
            question="Dans quelle équipe joue Anthony Edwards et quel est son pourcentage de lancers francs (FT%) ?",
        ),
        expected_output="Anthony Edwards joue pour 'MIN' (Minnesota) et son pourcentage de lancers francs (FT%) est de 83.7%.",
    ),
    Case(
        inputs=RagInputs(
            question="Quel est le Net Rating (NETRTG) de Shai Gilgeous-Alexander par rapport à Anthony Edwards ?",
        ),
        expected_output="Shai a un NETRTG de 16.7 tandis qu'Anthony Edwards a un NETRTG de 4.8.",
    ),
    Case(
        inputs=RagInputs(
            question="Donne-moi le nombre d'interceptions (STL) et de contres (BLK) pour Anthony Edwards.",
        ),
        expected_output="Anthony Edwards a réalisé 95 interceptions (STL) et 47 contres (BLK).",
    ),

    # ---------------------------------------------------------
    # CAS COMPLEXES (Nécessite des fonctions SQL : SUM, MAX, ORDER BY)
    # ---------------------------------------------------------
    Case(
        inputs=RagInputs(
            question="Combien de points au total l'équipe d'OKC a-t-elle marqués si l'on additionne tous ses joueurs dans la base ?",
        ),
        expected_output="Le modèle doit générer une requête SQL avec SUM(PTS) WHERE Team = 'OKC' pour donner le total des points des joueurs de cette équipe.",
    ),
    Case(
        inputs=RagInputs(
            question="Quel joueur a le plus de passes décisives (AST) dans cette base de données ?",
        ),
        expected_output="Le modèle doit effectuer un ORDER BY AST DESC LIMIT 1. Shai Gilgeous-Alexander est le joueur avec le plus d'AST (486) parmi les exemples connus.",
    ),

    # ---------------------------------------------------------
    # CAS LIMITES / PIÈGES (Évaluation de la robustesse SQL)
    # ---------------------------------------------------------
    # [PIÈGE - Fautes & Surnoms]
    Case(
        inputs=RagInputs(
            question="Combien de points a marqué SGA ou Shai Gilgeous Alexander (sans tiret) ?",
        ),
        expected_output="Le LLM doit comprendre que 'SGA' ou 'Shai Gilgeous Alexander' correspond à 'Shai Gilgeous-Alexander' dans la base et utiliser la clause LIKE ou formater correctement la chaîne. La réponse attendue est 2485 points.",
    ),
    # [PIÈGE - Entité Inexistante]
    Case(
        inputs=RagInputs(
            question="Quel est le pourcentage à 3 points de Michael Jordan ou LeBron James dans ce fichier ?",
        ),
        expected_output="Le tool SQL va s'exécuter et renvoyer un résultat vide. Le LLM doit répondre qu'il n'y a aucune donnée pour ces joueurs dans la base actuelle, sans halluciner de faux pourcentages.",
    ),
    # [PIÈGE - Mauvais domaine/colonne]
    Case(
        inputs=RagInputs(
            question="Combien de buts (goals) Anthony Edwards a-t-il marqués, et combien de cartons jaunes a-t-il reçus ?",
        ),
        expected_output="Le système ne doit pas inventer de colonnes 'goals' ou 'yellow_cards' dans la requête SQL. Il doit expliquer poliment que la base de données ne contient que des statistiques de basketball (NBA) et non de football, tout en proposant éventuellement les points (PTS) ou les fautes personnelles (PF).",
    ),
    # [PIÈGE - Ambiguïté de métrique]
    Case(
        inputs=RagInputs(
            question="Quel est le score de réussite à 3 points de Shai ?",
        ),
        expected_output="La question est ambiguë entre le nombre de tirs marqués (3PM), tentés (3PA) ou le pourcentage (3P%). Le modèle doit idéalement interroger ou retourner le pourcentage (3P%) qui est de 37.5%, tout en précisant peut-être les tirs réussis (160 3PM). Le modèle ne doit pas confondre ces trois colonnes SQL.",
    ),
    # [PIÈGE - Logique contraire]
    Case(
        inputs=RagInputs(
            question="Quel joueur a le pire (le plus bas) pourcentage de lancers francs (FT%) parmi ceux qui ont joué au moins 70 matchs (GP >= 70) ?",
        ),
        expected_output="Le modèle doit construire la requête : SELECT Player FROM table WHERE GP >= 70 ORDER BY FT% ASC LIMIT 1. Il doit bien comprendre 'le plus bas' comme un tri ascendant (ASC).",
    )
]

faithfulness = LLMJudge(
    rubric=(
        'The Output is a RagAnswer object with fields `answer`, `retrieved_contexts` (vector-search '
        'passages) and `sql_results` (executed SQL queries and their results). Every factual claim '
        'in the `answer` field must be directly supported by `retrieved_contexts` and/or '
        '`sql_results` in that same Output. Unsupported claims, contradictions, and fabrications '
        'constitute failure; ignore claims that are true in the real world but absent from the '
        'provided context. The score is the fraction of claims that are supported '
        '(0.0 = none, 1.0 = all); pass only if every claim is supported.'
    ),
    include_input=True,
    score={'evaluation_name': 'faithfulness'},
    assertion=False,
    model='google:gemini-3.5-flash-lite',
)

answer_relevance = LLMJudge(
    rubric=(
        'Judge whether the Output directly and completely answers the question in the Input, '
        'without padding or unrelated tangents. '
        'The score reflects how directly the Output addresses the question '
        '(0.0 = unrelated, 1.0 = a direct, on-point answer).'
    ),
    include_input=True,
    score={'evaluation_name': 'answer_relevance'},
    assertion=False,
    model='google:gemini-3.5-flash-lite',
)

context_precision = LLMJudge(
    rubric=(
        'The Output is a RagAnswer object with fields `answer`, `retrieved_contexts` (vector-search '
        'passages) and `sql_results` (executed SQL queries and their results). This metric judges '
        'the retrieval, not the answer: assess the passages in `retrieved_contexts` and '
        '`sql_results` against the question in the Input, and disregard the `answer` field. '
        'The score is the fraction of that retrieved context which is relevant to answering the '
        'question (0.0 = none is relevant, 1.0 = all of it is relevant). If both '
        '`retrieved_contexts` and `sql_results` are empty, score 0.0.'
    ),
    include_input=True,
    score={'evaluation_name': 'context_precision'},
    assertion=False,
    model='google:gemini-3.5-flash-lite',
)

context_recall = LLMJudge(
    rubric=(
        'The Output is a RagAnswer object with fields `answer`, `retrieved_contexts` (vector-search '
        'passages) and `sql_results` (executed SQL queries and their results). This metric judges '
        'the retrieval, not the answer: determine whether `retrieved_contexts` and `sql_results` '
        'together contain enough information to produce the ground-truth answer in the Expected '
        'Output, and disregard the `answer` field. The score is the fraction of the ground-truth '
        'answer that is supported by that retrieved context (0.0 = none of it, 1.0 = all of it). '
        'If the Expected Output is empty, score 1.0.'
    ),
    include_input=True,
    include_expected_output=True,
    score={'evaluation_name': 'context_recall'},
    assertion=False,
    model='google:gemini-3.5-flash-lite',
)

dataset = Dataset(
    name='rag_quality',
    cases=eval_cases,
    evaluators=[faithfulness, answer_relevance, context_precision, context_recall],
)

def rag_answer(inputs: RagInputs) -> RagAnswer:
    rag = Rag()
    response = rag.answer(inputs.question)
    return response

if __name__ == '__main__':

    logfire.configure()
    report = dataset.evaluate_sync(rag_answer)
