# Conception — TP3, partie I : Dog Guesser

Michel Jazeron — michel.jazeron@gmail.com

## L’organisation de l’application

L’application utilise Tkinter pour présenter une photo et quatre réponses possibles. Les images et la liste des races proviennent de Dog CEO. Les propositions reprennent les noms anglais de l’API et portent sur la race principale du chien.

La solution comprend aussi un serveur Python FastAPI. Le jeu consulte le record personnel par HTTP, transmet les scores et reçoit les changements du record global par WebSocket. Le serveur conserve les meilleurs scores dans un fichier JSON. Chaque résultat est également enregistré localement dans un fichier CSV.

Cette organisation permet de distinguer le jeu, la récupération des données et la gestion des records. Le serveur des records reste facultatif pour jouer : lorsque celui-ci est indisponible, l’interface le signale et le jeu peut continuer avec l’enregistrement local des résultats, à condition que les données de Dog CEO soient accessibles.

## L’expérience de jeu

Le barème proposé tient compte du temps de réponse : une bonne réponse rapporte 150 points en cinq secondes au maximum, 125 points jusqu’à dix secondes et 100 points au-delà. Une mauvaise réponse rapporte zéro point. L’interface indique la réponse attendue, le temps et le score après le choix du joueur.

La version améliorée permet d’enchaîner les questions avec le bouton « Rejouer ». La fenêtre est redimensionnable et une barre de défilement conserve l’accès au contenu sur les petits écrans. Les opérations réseau sont exécutées en arrière-plan pour préserver la réactivité de l’interface.

Pendant les essais, j’ai remplacé le libellé « Chargement… » du bouton désactivé par « Réponds pour rejouer » lorsque la question était prête. Ce changement explique mieux pourquoi le joueur doit répondre avant de passer à la question suivante.

## Mes vérifications et les difficultés rencontrées

J’ai vérifié le chargement des photos, l’affichage des réponses, le calcul du score, l’enregistrement local et la communication avec le serveur des records. J’ai également testé une nouvelle question après une réponse et contrôlé l’affichage des records.

Lorsqu’un message générique indiquait un échec de récupération des données, j’ai testé séparément la liste des races et le téléchargement d’une photo, d’abord avec PowerShell puis avec Python. Ces essais ont confirmé que les requêtes testées fonctionnaient au moment du diagnostic. J’ai aussi exécuté la fonction de préparation d’une question pour vérifier son résultat.

Une connexion aux records a ensuite été refusée parce que le serveur local n’était pas démarré. Après son lancement, j’ai constaté les échanges HTTP et l’ouverture du canal WebSocket. Enfin, j’ai enregistré les modifications dans Git et publié la version améliorée sur le dépôt public.

## Les limites de cette version

Le chargement de nouvelles questions nécessite une connexion Internet et dépend de la disponibilité de Dog CEO. Après une interruption de la connexion WebSocket aux records, il faut relancer le jeu pour se reconnecter.

Le serveur vérifie les valeurs de score autorisées, mais ne contrôle pas lui-même la réponse donnée au quiz : l’application ne comporte donc pas de mécanisme anti-triche. Le lancement prévu utilise un seul processus serveur. Ces limites sont décrites dans le README.
