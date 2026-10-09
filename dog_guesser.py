# Auteur : Michel Jazeron — michel.jazeron@gmail.com
# TP n°3 — Partie I : jeu Dog Guesser.
# Affiche un chien et demande une réponse parmi quatre races principales.

import json  # Permet de décoder les messages JSON reçus du serveur.
from queue import Queue, Empty  # Importe une file de messages utilisable entre deux fils d’exécution.
from threading import Thread  # Permet d’écouter le réseau sans bloquer la fenêtre.
from websockets.sync.client import connect  # Importe la connexion cliente WebSocket.
from websockets.exceptions import WebSocketException  # Importe les erreurs de communication WebSocket.

import random  # Importe les outils de sélection et de mélange aléatoires.
import tkinter as tk  # Importe les composants graphiques sous le nom court tk.
from PIL import Image, ImageTk  # Importe les outils de lecture et d’affichage des images.
from pathlib import Path  # Permet de manipuler le chemin du fichier image.
from urllib.parse import urlparse  # Permet d’extraire le chemin d’une adresse web.
import requests  # Permet de communiquer avec l’API et de télécharger l’image.
import csv  # Importe les outils de lecture et d’écriture des fichiers CSV.
from datetime import datetime  # Importe la gestion des dates et des heures.
from time import perf_counter  # Importe un chronomètre précis pour mesurer une durée.
URL_SERVEUR = "http://127.0.0.1:8000"  # Définit l’adresse du serveur des records.

def preparer_question() -> tuple[str, list[str]]:  # Prépare l’image et renvoie la bonne race ainsi que les quatre propositions.
    reponse = requests.get("https://dog.ceo/api/breeds/list/all", timeout=10)  # Demande la liste des races.
    reponse.raise_for_status()  # Vérifie l’absence d’erreur HTTP.
    donnees = reponse.json()  # Convertit la réponse JSON en données Python.
    if donnees.get("status") != "success" or not isinstance(donnees.get("message"), dict):  # Vérifie le contenu de la réponse.
        raise ValueError("La liste des races reçue est invalide.")  # Signale une réponse incorrecte.
    races: list[str] = list(donnees["message"])  # Récupère les noms des races principales.

    reponse = requests.get("https://dog.ceo/api/breeds/image/random", timeout=10)  # Demande une image aléatoire.
    reponse.raise_for_status()  # Vérifie l’absence d’erreur HTTP.
    donnees = reponse.json()  # Convertit la réponse en dictionnaire.
    adresse_image = donnees.get("message")  # Récupère l’adresse de l’image.
    if donnees.get("status") != "success" or not isinstance(adresse_image, str):  # Vérifie le contenu reçu.
        raise ValueError("La réponse concernant l’image est invalide.")  # Signale une réponse incorrecte.
    adresse = urlparse(adresse_image)  # Décompose l’adresse de l’image.
    morceaux = adresse.path.strip("/").split("/")  # Découpe le chemin en éléments.
    if adresse.scheme != "https" or len(morceaux) < 3 or morceaux[0] != "breeds":  # Vérifie le format attendu de l’adresse.
        raise ValueError("Le format de l’adresse de l’image est inattendu.")  # Signale un chemin inexploitable.
    bonne_race: str = morceaux[1].split("-")[0]  # Extrait la race principale, même lorsqu’une sous-race est indiquée.
    if bonne_race not in races:  # Vérifie que la race extraite appartient à la liste de l’API.
        raise ValueError("La race de l’image est absente de la liste reçue.")  # Signale une incohérence.

    autres_races: list[str] = [race for race in races if race != bonne_race]  # Exclut la bonne réponse des mauvaises propositions.
    propositions: list[str] = random.sample(autres_races, 3)  # Tire trois mauvaises réponses différentes.
    propositions.append(bonne_race)  # Ajoute la bonne réponse aux propositions.
    random.shuffle(propositions)  # Mélange les quatre propositions.

    image = requests.get(adresse_image, timeout=10)  # Télécharge les octets de l’image.
    image.raise_for_status()  # Vérifie que le téléchargement a réussi.
    chemin = Path(__file__).resolve().parent / "chien_mystere.jpg"  # Prépare un nom neutre dans le dossier du script.
    with open(chemin, "wb") as fichier:  # Ouvre le fichier en écriture binaire pour enregistrer une image.
        fichier.write(image.content)  # Enregistre les octets téléchargés.
    
    return bonne_race, propositions  # Renvoie les informations nécessaires au jeu.

def calculer_score(bonne_reponse: bool, duree: float) -> int:  # Calcule les points selon la justesse et la durée en secondes.
    if not bonne_reponse:  # Vérifie si le joueur a donné une mauvaise réponse.
        return 0  # Attribue zéro point pour une mauvaise réponse.
    if duree <= 5:  # Vérifie si la bonne réponse a été donnée en cinq secondes maximum.
        return 150  # Attribue cent points et un bonus de cinquante points.
    if duree <= 10:  # Vérifie si la bonne réponse a été donnée en dix secondes maximum.
        return 125  # Attribue cent points et un bonus de vingt-cinq points.
    return 100  # Attribue cent points pour une bonne réponse plus lente.


def sauvegarder_score(bonne_race: str, choix: str, duree: float, score: int) -> None:  # Enregistre le résultat d’une question dans un fichier local.
    chemin = Path(__file__).resolve().parent / "scores_dog_guesser.csv"  # Place le fichier des résultats à côté du script.
    champs = ["horodatage", "joueur", "email", "race_attendue", "reponse", "bonne_reponse", "duree_secondes", "score"]  # Définit les colonnes du fichier.
    with open(chemin, "a", encoding="utf-8", newline="") as fichier:  # Ouvre le fichier en ajout, le crée si nécessaire et garantit sa fermeture.
        redacteur = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")  # Prépare l’écriture de dictionnaires avec un séparateur point-virgule.
        if fichier.tell() == 0:  # Vérifie que le fichier est vide avant d’ajouter les noms des colonnes.
            redacteur.writeheader()  # Écrit la ligne d’en-tête une seule fois.
        resultat = {  # Prépare les informations à sauvegarder pour cette réponse.
            "horodatage": datetime.now().isoformat(timespec="seconds"),  # Enregistre la date et l’heure locales à la seconde près.
            "joueur": "Michel Jazeron",  # Enregistre le nom du joueur.
            "email": "michel.jazeron@gmail.com",  # Enregistre l’adresse du joueur.
            "race_attendue": bonne_race,  # Enregistre la bonne réponse.
            "reponse": choix,  # Enregistre la race choisie.
            "bonne_reponse": choix == bonne_race,  # Indique si la réponse est correcte.
            "duree_secondes": round(duree, 3),  # Enregistre la durée arrondie à trois décimales.
            "score": score,  # Enregistre les points obtenus.
        }  # Termine le dictionnaire du résultat.
        redacteur.writerow(resultat)  # Ajoute une ligne sans effacer les résultats précédents.


def lire_record(joueur: str) -> int:  # Demande au serveur le record du joueur.
    reponse = requests.get(f"{URL_SERVEUR}/record", params={"joueur": joueur}, timeout=5)  # Envoie une demande HTTP avec le nom du joueur.
    reponse.raise_for_status()  # Déclenche une exception si le serveur renvoie une erreur HTTP.
    return int(reponse.json()["record"])  # Récupère le record dans la réponse JSON.

def envoyer_score(joueur: str, score: int) -> int:  # Transmet un score au serveur et renvoie le record sauvegardé.
    donnees = {"joueur": joueur, "score": score}  # Prépare les données à transmettre.
    reponse = requests.post(f"{URL_SERVEUR}/score", json=donnees, timeout=5)  # Envoie les données au serveur au format JSON.
    reponse.raise_for_status()  # Vérifie que le serveur a accepté et traité la demande.
    return int(reponse.json()["record"])  # Renvoie le record confirmé par le serveur.

def ecouter_records(messages: Queue) -> None:  # Reçoit les records du serveur dans un fil d’exécution séparé.
    try:  # Tente d’ouvrir une connexion persistante avec le serveur.
        with connect("ws://127.0.0.1:8000/ws/records", open_timeout=5) as connexion:  # Ouvre le canal WebSocket et garantit sa fermeture.
            for message in connexion:  # Attend les messages envoyés par le serveur.
                donnees = json.loads(message)  # Transforme le message JSON en dictionnaire Python.
                messages.put(donnees)  # Transmet les informations à la fenêtre par une file de messages.
    except (OSError, WebSocketException, ValueError) as erreur:  # Intercepte une erreur réseau ou un message JSON invalide.
        print(f"Michel, connexion aux records interrompue : {erreur}")  # Affiche le détail dans le terminal.
    finally:  # Signale aussi une fermeture normale de la connexion.
        messages.put({"erreur": "Connexion aux records interrompue : relance le jeu."})  # Informe l’interface que les données ne sont plus actualisées.

def afficher_question(bonne_race: str, propositions: list[str]) -> None:  # Affiche la question et gère la réponse du joueur.
    fenetre = tk.Tk()  # Crée la fenêtre principale du jeu.
    fenetre.title("Dog Guesser — Michel Jazeron")  # Définit le titre de la fenêtre.
    fenetre.resizable(False, False)  # Empêche le redimensionnement manuel de la fenêtre.

    titre = tk.Label(fenetre, text="Michel, quelle est la race principale de ce chien ?", font=("Arial", 14))  # Crée le texte de la question.
    titre.pack(padx=20, pady=10)  # Affiche la question avec des marges.
    record_joueur = lire_record("Michel Jazeron")  # Charge le meilleur score de Michel avant de commencer la question.
    zone_record = tk.Label(fenetre, text=f"Record de Michel Jazeron : {record_joueur} points", font=("Arial", 12), fg="navy")  # Crée le texte du record en bleu foncé.
    zone_record.pack(pady=5)  # Affiche le record sous le titre.
    zone_global = tk.Label(fenetre, text="Record de tous les temps : connexion…", font=("Arial", 12), fg="purple", wraplength=580)  # Prépare l’affichage du record global.
    zone_global.pack(pady=5)  # Affiche le record global sous le record personnel.
    messages_records = Queue()  # Crée la file reliant la réception réseau à l’interface.

    def actualiser_record_global() -> None:  # Traite les notifications dans le fil principal de Tkinter.
        try:  # Consulte les messages déjà reçus sans attendre le réseau.
            while True:  # Traite tous les messages disponibles.
                donnees = messages_records.get_nowait()  # Retire le prochain message sans bloquer la fenêtre.
                if "erreur" in donnees:  # Vérifie si la connexion a été interrompue.
                    zone_global.config(text=donnees["erreur"], fg="firebrick")  # Signale que l’actualisation n’est plus disponible.
                else:  # Traite un record envoyé par le serveur.
                    noms = ", ".join(donnees["joueurs"]) or "Aucun joueur"  # Prépare la liste des détenteurs du record.
                    texte = f"Record de tous les temps : {donnees['record']} points\nDétenu par : {noms}"  # Prépare le texte à afficher.
                    zone_global.config(text=texte, fg="purple")  # Actualise le record global dans la fenêtre.
        except Empty:  # Détecte que tous les messages disponibles ont été traités.
            pass  # Termine cette vérification sans bloquer l’interface.
        fenetre.after(100, actualiser_record_global)  # Programme la prochaine consultation de la file dans cent millisecondes.

    Thread(target=ecouter_records, args=(messages_records,), daemon=True).start()  # Démarre l’écoute réseau en arrière-plan sans empêcher la fermeture du programme.
    actualiser_record_global()  # Lance le traitement des notifications par l’interface.
    chemin = Path(__file__).resolve().parent / "chien_mystere.jpg"  # Retrouve l’image téléchargée à côté du script.
    with Image.open(chemin) as image:  # Ouvre l’image et garantit la fermeture du fichier.
        image.thumbnail((600, 400))  # Limite les dimensions de l’image en conservant ses proportions.
        photo = ImageTk.PhotoImage(image)  # Convertit l’image pour son affichage dans Tkinter.

    zone_image = tk.Label(fenetre, image=photo)  # Crée la zone contenant la photographie.
    zone_image.pack(padx=20, pady=10)  # Affiche la photographie dans la fenêtre.
    zone_global.config(wraplength=480, justify="center")  # Limite la largeur du texte et centre les lignes pour garder les noms visibles.

    indication = tk.Label(fenetre, text="Clique sur une race. Les noms sont ceux de l’API, en anglais.")  # Crée la consigne de réponse.
    indication.pack(pady=5)  # Affiche la consigne sous la photographie.

    cadre_boutons = tk.Frame(fenetre)  # Crée un conteneur pour les quatre boutons.
    cadre_boutons.pack(padx=20, pady=10)  # Positionne le conteneur dans la fenêtre.

    resultat = tk.Label(fenetre, text="", font=("Arial", 13), wraplength=580)  # Prépare une zone de résultat avec retour automatique à la ligne.
    resultat.pack(padx=20, pady=10)  # Positionne la zone de résultat sous les boutons.

    boutons: list[tk.Button] = []  # Prépare la liste des boutons à désactiver après la réponse.

    def verifier_reponse(choix: str) -> None:  # Définit la fonction appelée lorsqu’un joueur clique sur une race.
        duree = perf_counter() - debut_question  # Calcule le temps de réponse en secondes.
        bonne_reponse = choix == bonne_race  # Vérifie si le choix correspond à la race attendue.
        score = calculer_score(bonne_reponse, duree)  # Calcule les points selon la justesse et la rapidité.

        for bouton in boutons:  # Parcourt les boutons de réponse.
            bouton.config(state=tk.DISABLED)  # Désactive le bouton pour empêcher une seconde réponse.

        if bonne_reponse:  # Traite une réponse correcte.
            message = f"Bonne réponse, Michel ! Il s’agit de : {bonne_race}."  # Prépare le message de réussite.
            couleur = "darkgreen"  # Utilise du vert foncé pour la réussite.
        else:  # Traite une réponse incorrecte.
            message = f"Mauvaise réponse, Michel. Tu as choisi {choix}. La bonne réponse est : {bonne_race}."  # Prépare la correction.
            couleur = "firebrick"  # Utilise une couleur rouge pour l’erreur.

        message += f"\nTemps : {duree:.2f} secondes — Score : {score} points."  # Ajoute le temps et les points obtenus.

        try:  # Tente de conserver chaque résultat dans le fichier CSV local.
            sauvegarder_score(bonne_race, choix, duree, score)  # Enregistre la réponse, sa durée et ses points.
        except OSError as erreur:  # Intercepte une erreur d’écriture sans empêcher l’envoi au serveur.
            message += "\nScore non sauvegardé dans le fichier local."  # Signale l’échec de la sauvegarde CSV.
            print(f"Michel, erreur de sauvegarde locale : {erreur}")  # Affiche la cause dans le terminal.
        else:  # Confirme une écriture locale réussie.
            message += "\nScore sauvegardé dans scores_dog_guesser.csv."  # Indique le fichier contenant le résultat.

        try:  # Tente d’envoyer le score au serveur.
            nouveau_record = envoyer_score("Michel Jazeron", score)  # Demande au serveur de sauvegarder le record.
        except (requests.exceptions.RequestException, ValueError, KeyError) as erreur:  # Intercepte une erreur réseau ou une réponse inexploitable.
            message += "\nRecord non sauvegardé : communication avec le serveur impossible."  # Signale clairement l’échec.
            print(f"Michel, erreur de communication avec le serveur : {erreur}")  # Affiche le détail dans le terminal.
        else:  # Actualise l’interface uniquement après la confirmation du serveur.
            zone_record.config(text=f"Record de Michel Jazeron : {nouveau_record} points")  # Affiche le record renvoyé par le serveur.
            message += "\nRecord sauvegardé sur le serveur."  # Confirme la sauvegarde côté serveur.
            if nouveau_record > record_joueur:  # Compare le record obtenu avec celui chargé au début de la question.
                message += "\nNouveau record personnel, Michel !"  # Annonce un nouveau record.

        resultat.config(text=message, fg=couleur)  # Affiche le résultat complet dans la fenêtre.

    for position, race in enumerate(propositions):  # Parcourt les quatre races pour créer les boutons.
        bouton = tk.Button(cadre_boutons, text=race, width=24, font=("Arial", 12), command=lambda choix=race: verifier_reponse(choix))  # Associe chaque bouton à sa propre race.
        bouton.grid(row=position // 2, column=position % 2, padx=5, pady=5)  # Dispose les boutons sur deux lignes et deux colonnes.
        boutons.append(bouton)  # Conserve le bouton pour pouvoir le désactiver après la réponse.

    signature = tk.Label(fenetre, text="Michel Jazeron — michel.jazeron@gmail.com", fg="gray")  # Crée la signature du joueur.
    signature.pack(pady=10)  # Affiche la signature en bas de la fenêtre.

    debut_question = perf_counter()  # Démarre le chronomètre une fois les éléments de la fenêtre préparés.
    fenetre.mainloop()  # Lance la boucle principale qui affiche la fenêtre et traite les clics.

if __name__ == "__main__":  # Lance le jeu uniquement lorsque ce fichier est exécuté directement.
    print("Michel, préparation de la photo et des quatre propositions…")  # Signale le chargement avant l’ouverture de la fenêtre.
    try:  # Tente de préparer et d’afficher la question.
        bonne_race, propositions = preparer_question()  # Télécharge l’image et prépare les quatre choix.
        afficher_question(bonne_race, propositions)  # Ouvre la fenêtre et attend le clic du joueur.
    except requests.exceptions.RequestException:  # Intercepte les erreurs réseau et HTTP.
        print("Michel, impossible de récupérer les données. Vérifie ta connexion et réessaie.")  # Signale un problème de communication.
    except ValueError as erreur:  # Intercepte les données incorrectes.
        print(f"Michel, les données reçues sont invalides : {erreur}")  # Affiche le problème rencontré.
    except OSError as erreur:  # Intercepte notamment les erreurs d’écriture ou de lecture de l’image.
        print(f"Michel, impossible de traiter l’image : {erreur}")  # Explique le problème concernant l’image.
