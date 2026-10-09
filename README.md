# TP3 — Dog Guesser

Michel Jazeron — michel.jazeron@gmail.com

Jeu Python : reconnaître la race principale d’un chien parmi quatre boutons. Photos issues de Dog CEO, interface Tkinter, serveur FastAPI et actualisation du record global par WebSocket (connexion persistante permettant au serveur d’envoyer les changements).

## Installation sous Windows / PowerShell

Prérequis : Python 3.13 avec Tcl/Tk installé, un environnement graphique et une connexion Internet. Ouvrir un terminal dans le dossier du projet téléchargé depuis GitHub, puis exécuter :

```powershell
python -m venv .venv # Crée un environnement Python isolé.
.\.venv\Scripts\python.exe -m pip install -r requirements.txt # Installe les dépendances du projet.
```

Tkinter et les autres modules standards ne s’installent pas avec ce fichier. Les six dépendances directes sont listées ; leurs dépendances indirectes sont installées automatiquement.

## Lancement

Dans un premier terminal, ouvert dans le dossier du projet :

```powershell
.\.venv\Scripts\python.exe -m uvicorn serveur_records:app --host 127.0.0.1 --port 8000 # Démarre le serveur local ; laisser ce terminal ouvert.
```

Dans un second terminal, ouvert dans le même dossier :

```powershell
.\.venv\Scripts\python.exe .\dog_guesser.py # Lance une question du jeu pour Michel Jazeron.
```

Cliquer sur une race. Fermer puis relancer le jeu pour une nouvelle question. Arrêter le serveur avec Ctrl+C. Après une interruption du canal WebSocket, relancer le jeu pour se reconnecter. Utiliser un seul processus serveur, sans option multi-processus.

Pour les exercices de prise en main :

```powershell
.\.venv\Scripts\python.exe .\test_request.py # Compte les races principales et ouvre une photo dans le navigateur.
```

## Scores et fichiers

Mauvaise réponse : 0 point. Bonne réponse en 5 secondes maximum : 150 points ; en plus de 5 et au plus 10 secondes : 125 points ; au-delà : 100 points. Chaque résultat est ajouté à `scores_dog_guesser.csv` côté jeu. Le serveur conserve le meilleur score de chaque joueur dans `records.json`, créé au premier envoi. Ces fichiers et `chien_mystere.jpg` sont générés automatiquement et exclus du dépôt.

`GET /record?joueur=Michel%20Jazeron` consulte le record personnel ; `POST /score` reçoit un nom et un score ; `/ws/records` diffuse le record global et ses détenteurs, y compris les ex æquo. Le serveur valide le barème mais ne vérifie pas lui-même la réponse au quiz : ce TP ne comporte pas de mécanisme anti-triche.
