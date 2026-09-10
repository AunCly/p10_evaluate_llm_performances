# Mission
Vous venez d’intégrer SportSee, une startup spécialisée dans l’IA appliquée à l’analyse de la performance sportive en tant que Data Scientist. Vous intégrez l’équipe R&D en charge de la construction d’un assistant intelligent d’analyse de performance.
SportSee travaille avec des clubs de basketball pour valoriser leurs archives vidéo, leurs rapports d’analyse et leurs données de matchs.
L’objectif : aider les entraîneurs, analystes et préparateurs physiques à trouver plus rapidement les informations clés pour préparer les entraînements, les matchs ou suivre la progression des athlètes.
Quelques jours après votre arrivée, vous recevez un mail de Sarah, une Data Scientist de l’équipe, elle a besoin de votre aide.

## Détails
> De : Sarah
> À : moi
> Objet : Assistant IA fonctionnel
> Hello !
>J'espère que tu as bien pris tes marques.
>Nous avons un prototype d'assistant IA fonctionnel qui donne des résultats encourageants sur nos archives textuelles. Tu trouveras le code en pièce jointe.
>Cependant, pour qu'il devienne vraiment indispensable pour les coachs, il doit pouvoir répondre à des questions précises comme : "Quel joueur a le meilleur pourcentage de réussite à 3 points sur les 5 derniers matchs ?" ou "Compare les statistiques de rebonds de l'équipe à domicile et à l'extérieur."
>Aujourd'hui, nous ne sommes pas satisfaits des réponses de notre solution. Commence à consulter le prototype, je te donne les détails de la mission sur Slack dans quelques minutes.
>Bonne journée !
>Sarah

Vous recevez de nouveau un e-mail de Sarah qui vous précise les prochaines étapes de votre projet.

De : Sarah
À : Moi
Objet : Consignes détaillées – Audit, extension et documentation du prototype RAG pour le Rapport de mise en place et d'évaluation du système RAG.
Hello !
Voici le cadrage détaillé des prochaines étapes.
Ces travaux vont te permettre de renforcer la fiabilité, la robustesse et la traçabilité de notre assistant IA, pour le rendre exploitable en production et adaptable à d’autres clubs.
Je t’invite à avoir un regard critique, en prenant soin de documenter systématiquement tes choix, tes méthodes et tes constats.
Voici les étapes que je te recommande :
Étape 1 : Évaluation structurée du prototype existant

Cette phase permet de produire des métriques objectives sur les performances actuelles du système, afin d’identifier les axes d’amélioration.

Ce que j’attends de toi dans un Repo Git :
Développer un script Python d’évaluation (evaluate_ragas.py) basé sur RAGAS, mesurant la pertinence des réponses du prototype à partir d’un jeu de questions métiers (ex. : « Quel joueur a le meilleur % à 3 points sur les 5 derniers matchs ? »).
Mettre en place un pipeline de préparation des données (chunking, nettoyage, embedding) validé avec Pydantic et Pydantic AI, pour sécuriser les flux d’entrée et de sortie.
Intégrer Pydantic Logfire afin de visualiser pas à pas le fonctionnement de la chaîne RAG/LLM lors de son exécution.

Conseil : Prends le temps de définir et catégoriser tes cas de tests (simples, complexes, bruités…), en t’appuyant sur des exemples métier réalistes. Croise ces cas avec les scores obtenus et synthétise le tout dans un tableau comparatif.

Étape 2 : Intégration des données Excel et création d’un Tool SQL

L’objectif de cette phase est d’enrichir l’agent avec les données (que je te redonne en pièces jointes).

Ce que j’attends de toi :
Modélisation de la base : schéma relationnel (PostgreSQL ou SQLite) pour les tablesplayers,matches,stats,reportsavec clés appropriées.
Création du pipeline d’ingestion (load_excel_to_db.py) :
Lecture des fichiers Excel.
Validation des données via Pydantic.
Insertion dans la base de données.
Tool LangChain SQL (sql_tool.py) :
Génération dynamique de requêtes SQL à partir de la question de l’utilisateur.
Exécution des requêtes et retour des résultats.
Mise en place de quelques exemples few-shot pour améliorer la précision des templates SQL.
Mise à jour de l’agent : intégrer ce Tool pour que le LLM détecte les questions chiffrées, appelle le Tool, puis synthétise la réponse.
Conseil : Documente la structure de la base et fournis des exemples de requêtes types (comparaison domicile/extérieur, agrégations multicritères, etc.).

Étape 3 : Seconde évaluation et comparatif

Cette phase permettra de mesurer l’impact de l’enrichissement chiffré sur la pertinence et la robustesse.
Ce que j’attends de toi :
Réexécuter les tests avecevaluate_ragas.pyet comparer les scores avant/après.
Étendre les tests de robustesse aux scénarios mêlant texte et données numériques.
Analyser de façon critique les biais et limites (mapping NL→SQL, couverture des cas, etc.).

Conseil : Présente les résultats dans un rapport comparatif, avec un tableau synthétique et des graphiques simples pour illustrer l’évolution des performances.

Intègre ensuite tout ton travail réalisé au cours de ces étapes dans un Rapport de mise en place et d'évaluation du système RAG.

Merci et bon courage !

Cordialement,

Sarah
Data Scientist – SportSee

## Choix techniques et méthodologiques

J'ai vu avec la mentor : 
- Je ne vais pas utiliser ragas car la librairie est abandonné depuis 7 mois et ne fonctionne pas avec les dernières versions de langchain.
- Je vais utilise le système de validation de pydantic pour valider les entrées et sorties du système RAG : https://pydantic.dev/docs/validation/latest/get-started/
- Je vais utiliser pydantic AI à la place de langchain : https://pydantic.dev/docs/ai/overview/
- Je vais utiliser logfire pour visualiser le fonctionnement du système RAG : https://pydantic.dev/docs/logfire/get-started/
- Je vais utiliser Pydandic eval pour évaluer les performances du système RAG : https://pydantic.dev/docs/ai/evals/evals/
- Je vais utiliser Google Gemini à la place de mistral.