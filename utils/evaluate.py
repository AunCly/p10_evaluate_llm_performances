from dataclasses import dataclass

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from schemas.rag_io import RagAnswer
from utils.rag import Rag


@dataclass
class RagInputs:
    question: str
    context: list[str]

cases = [
    Case(
        inputs=RagInputs(
            question='De quoi parle la discussion Reddit sur l\'avantage du terrain en finale NBA ?',
            context=[''],
        ),
        expected_output='',
    ),
    Case(
        inputs=RagInputs(
            question='Quels sont les arguments soulevés dans les threads Reddit concernant les équipes qui impressionnent le plus en playoffs ?',
            context=[''],
        ),
        expected_output='',
    ),
    Case(
        inputs=RagInputs(
            question='Quel joueur a le meilleur % à 3 points sur les 5 derniers matchs ?',
            context=[''],
        ),
        expected_output='Le joueur avec le meilleur pourcentage à 3 points sur les 5 derniers matchs est PJ Dozier, avec un pourcentage de 66.7%.',
    ),
    Case(
        inputs=RagInputs(
            question='Quel joueur a le meilleur % à 3 points sur les 5 derniers matchs ?',
            context=[''],
        ),
        expected_output='',
    ),
    Case(
        inputs=RagInputs(
            question='Quel joueur a le meilleur PIE de la saison ?',
            context=[''],
        ),
        expected_output='',
    ),
]

faithfulness = LLMJudge(
    rubric=(
        'Every factual claim in the Output must be directly supported by the context passages '
        'in the Input. Unsupported claims, contradictions, and fabrications constitute failure; '
        'ignore claims that are true in the real world but absent from the provided context. '
        'The score is the fraction of claims that are supported (0.0 = none, 1.0 = all); '
        'pass only if every claim is supported.'
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
        'This metric judges the retrieval, not the answer: assess the context passages in the '
        'Input against the question in the Input, and disregard the Output. '
        'The score is the fraction of the context that is relevant to answering the question '
        '(0.0 = none is relevant, 1.0 = all of it is relevant).'
    ),
    include_input=True,
    score={'evaluation_name': 'context_precision'},
    assertion=False,
    model='google:gemini-3.5-flash-lite',
)

context_recall = LLMJudge(
    rubric=(
        'This metric judges the retrieval, not the answer: determine whether the context '
        'passages in the Input contain enough information to produce the ground-truth answer '
        'in the Expected Output, and disregard the Output. '
        'The score is the fraction of the ground-truth answer that is supported by the context '
        '(0.0 = none of it, 1.0 = all of it).'
    ),
    include_input=True,
    include_expected_output=True,
    score={'evaluation_name': 'context_recall'},
    assertion=False,
    model='google:gemini-3.5-flash-lite',
)

dataset = Dataset(
    name='rag_quality',
    cases=cases,
    evaluators=[faithfulness, answer_relevance, context_precision, context_recall],
)

def rag_answer(inputs: RagInputs) -> str:
    rag = Rag()

    response = rag.answer(inputs.question)

    return response.answer

if __name__ == '__main__':
    report = dataset.evaluate_sync(rag_answer)
    print(report)
    # Print results
    report.print(include_input=True, include_output=True)