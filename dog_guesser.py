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

class Jeu:  # Regroupe l’interface et l’état de la question en cours.
    def __init__(self) -> None:  # Prépare une seule fenêtre réutilisée pour toutes les questions.
        self.fenetre = tk.Tk()  # Crée la fenêtre dans le fil principal.
        self.fenetre.title("Dog Guesser — Michel Jazeron")  # Nomme la fenêtre.
        self.fenetre.protocol("WM_DELETE_WINDOW", self.fermer)  # Termine une sauvegarde commencée avant de fermer.
        largeur = min(720, self.fenetre.winfo_screenwidth() - 80)  # Adapte la largeur à l’écran.
        hauteur = min(850, self.fenetre.winfo_screenheight() - 100)  # Réserve de la place aux bordures et à la barre des tâches.
        self.fenetre.geometry(f"{largeur}x{hauteur}+20+20")  # Positionne une fenêtre redimensionnable dans l’écran.
        self.messages = Queue()  # Reçoit les résultats des opérations HTTP.
        self.records = Queue()  # Reçoit les notifications WebSocket.
        self.phase = "repos"  # Distingue chargement, question, sauvegarde et repos.
        self.record = None  # Distingue un record inconnu d’un record égal à zéro.
        self.photo_source = None  # Conserve l’image originale pour les redimensionnements.
        self.bonne_race = ""  # Initialise la réponse attendue.
        self.numero = 0  # Compte les questions effectivement affichées.
        self.debut = 0.0  # Initialise le chronomètre.
        self.surface = tk.Canvas(self.fenetre, highlightthickness=0, bg="#f3f6fa")  # Crée une zone de contenu défilante.
        barre = tk.Scrollbar(self.fenetre, orient="vertical", command=self.surface.yview)  # Permet de parcourir une fenêtre trop petite.
        barre.pack(side="right", fill="y")  # Place la barre sur le bord droit.
        self.surface.pack(side="left", fill="both", expand=True)  # Adapte la zone à la fenêtre.
        self.surface.config(yscrollcommand=barre.set)  # Synchronise la position de la barre.
        self.contenu = tk.Frame(self.surface, bg="#f3f6fa", padx=12, pady=12)  # Regroupe les éléments du jeu.
        self.element = self.surface.create_window(0, 0, window=self.contenu, anchor="nw")  # Insère le contenu dans la zone défilante.
        self.contenu.bind("<Configure>", lambda evenement: self.surface.config(scrollregion=self.surface.bbox("all")))  # Actualise la hauteur défilable.
        self.textes = []  # Conserve les textes dont la largeur doit s’adapter.
        self.titre = self.texte("Dog Guesser", 19, "#16324f")  # Affiche le nom du jeu.
        self.texte("Michel, retrouve la race principale de ce chien.", 12)  # Affiche la consigne.
        self.personnel = self.texte("Record personnel : chargement…", 11, "#16324f")  # Prépare le record individuel.
        self.global_ = self.texte("Record de tous les temps : connexion…", 11, "#643a87")  # Prépare le record global.
        self.image = tk.Label(self.contenu, bg="#f3f6fa")  # Prépare la photographie.
        self.image.pack(pady=8)  # Centre la photographie.
        self.etat = self.texte("", 11, "#16324f")  # Indique la progression ou les erreurs.
        self.texte("Bonne réponse : ≤ 5 s = 150 pts ; ≤ 10 s = 125 pts ; sinon 100 pts.\nMauvaise réponse : 0 point. Noms des races en anglais, comme dans l’API.", 10)  # Explique le barème avant de jouer.
        cadre = tk.Frame(self.contenu, bg="#f3f6fa")  # Regroupe les choix en deux colonnes.
        cadre.pack(fill="x", pady=8)  # Utilise toute la largeur disponible.
        cadre.columnconfigure((0, 1), weight=1, uniform="choix")  # Donne la même largeur aux deux colonnes.
        self.boutons = []  # Conserve les quatre boutons.
        for position in range(4):  # Crée les boutons une seule fois.
            bouton = tk.Button(cadre, text="…", font=("Arial", 11), state="disabled", pady=7)  # Prépare un bouton de réponse.
            bouton.grid(row=position // 2, column=position % 2, sticky="ew", padx=4, pady=4)  # Organise les choix en grille.
            self.boutons.append(bouton)  # Mémorise le bouton.
        self.resultat = self.texte("", 11)  # Affiche la correction et les confirmations de sauvegarde.
        self.rejouer = tk.Button(self.contenu, text="Rejouer", command=self.charger, font=("Arial", 11), pady=6)  # Propose une nouvelle question sans relancer Python.
        self.rejouer.pack(fill="x", pady=6)  # Place le bouton sous le résultat.
        self.texte("Michel Jazeron — michel.jazeron@gmail.com", 9, "#596579")  # Affiche la signature.
        self.surface.bind("<Configure>", self.adapter)  # Adapte textes et photographie au redimensionnement.
        self.fenetre.bind("<MouseWheel>", self.defiler)  # Active la molette sous Windows.
        self.fenetre.bind("<Button-4>", lambda evenement: self.surface.yview_scroll(-1, "units"))  # Active le défilement vers le haut sous Linux.
        self.fenetre.bind("<Button-5>", lambda evenement: self.surface.yview_scroll(1, "units"))  # Active le défilement vers le bas sous Linux.
        Thread(target=ecouter_records, args=(self.records,), daemon=True).start()  # Ouvre une seule connexion WebSocket pour toute la session.
        self.fenetre.after(50, self.traiter)  # Programme le traitement des messages dans le fil graphique.
        self.charger()  # Charge la première question en arrière-plan.

    def fermer(self) -> None:  # Évite de couper une écriture en cours.
        if self.phase == "sauvegarde":  # Vérifie si le résultat est encore en cours d’enregistrement.
            self.etat.config(text="Sauvegarde en cours : attends sa fin, puis ferme la fenêtre.")  # Explique pourquoi la fermeture est différée.
            return  # Laisse se terminer les opérations bornées par leurs délais réseau.
        self.fenetre.destroy()  # Ferme normalement dans les autres états.

    def texte(self, valeur: str, taille: int, couleur: str = "#243447") -> tk.Label:  # Crée un texte adaptable et centré.
        zone = tk.Label(self.contenu, text=valeur, font=("Arial", taille), fg=couleur, bg="#f3f6fa", justify="center", wraplength=480)  # Définit son apparence.
        zone.pack(fill="x", pady=4)  # Affiche le texte avec une marge réduite.
        self.textes.append(zone)  # Permet de recalculer sa largeur.
        return zone  # Renvoie le composant pour les mises à jour.

    def defiler(self, evenement) -> None:  # Traduit le mouvement de la molette en défilement.
        if evenement.delta:  # Ignore un événement sans mouvement.
            self.surface.yview_scroll(-1 if evenement.delta > 0 else 1, "units")  # Déplace le contenu dans le sens demandé.

    def adapter(self, evenement=None) -> None:  # Adapte les éléments à la taille courante.
        largeur = max(100, self.surface.winfo_width() - 32)  # Calcule la largeur utile.
        self.surface.itemconfigure(self.element, width=self.surface.winfo_width())  # Ajuste le conteneur au cadre visible.
        for zone in self.textes:  # Parcourt les textes de l’interface.
            zone.config(wraplength=largeur)  # Évite les textes coupés horizontalement.
        for bouton in self.boutons:  # Parcourt les choix.
            bouton.config(wraplength=max(60, largeur // 2 - 20))  # Autorise les noms longs sur plusieurs lignes.
        if self.photo_source is not None:  # Redimensionne uniquement lorsqu’une photo est disponible.
            image = self.photo_source.copy()  # Préserve la qualité de l’original.
            image.thumbnail((min(580, largeur), max(120, min(330, self.fenetre.winfo_height() // 3))))  # Adapte la photo à la largeur et à la hauteur.
            self.photo = ImageTk.PhotoImage(image)  # Conserve une référence à l’image Tkinter.
            self.image.config(image=self.photo)  # Actualise la photographie affichée.

    def charger(self) -> None:  # Prépare une nouvelle question uniquement lorsque la précédente est terminée.
        if self.phase != "repos":  # Empêche deux chargements simultanés.
            return  # Ignore un clic prématuré.
        self.phase = "chargement"  # Verrouille les actions pendant le téléchargement.
        self.rejouer.config(state="disabled", text="Chargement…")  # Indique que la demande est en cours.
        self.resultat.config(text="")  # Efface l’ancien résultat.
        self.etat.config(text="Chargement de la photo…", fg="#16324f")  # Affiche une progression explicite.
        self.photo_source = None  # Retire l’ancienne photographie du redimensionnement.
        self.image.config(image="")  # Masque l’image précédente.
        for bouton in self.boutons:  # Réinitialise les quatre choix.
            bouton.config(text="…", state="disabled")  # Interdit les réponses pendant le téléchargement.
        self.surface.yview_moveto(0)  # Revient au début du contenu.
        Thread(target=self.telecharger, daemon=True).start()  # Effectue les requêtes sans bloquer les clics de la fenêtre.

    def telecharger(self) -> None:  # Travaille hors du fil graphique sans modifier Tkinter.
        try:  # Essaie de récupérer le record personnel.
            self.messages.put(("record", lire_record("Michel Jazeron")))  # Transmet le record à la fenêtre.
        except (requests.exceptions.RequestException, ValueError, KeyError):  # Traite un serveur indisponible ou une réponse invalide.
            self.messages.put(("record_indisponible", None))  # Autorise le jeu avec une sauvegarde locale.
        try:  # Essaie de préparer la question et son image.
            race, propositions = preparer_question()  # Réutilise l’API Dog CEO et les quatre propositions.
            with Image.open(Path(__file__).resolve().parent / "chien_mystere.jpg") as image:  # Ouvre la photographie téléchargée.
                photo = image.copy()  # Charge les pixels avant de fermer le fichier.
            self.messages.put(("question", (race, propositions, photo)))  # Transmet une question complète.
        except (requests.exceptions.RequestException, OSError, ValueError, KeyError, AttributeError) as erreur:  # Intercepte les erreurs réseau, image et données.
            self.messages.put(("erreur", f"Chargement impossible : {erreur}"))  # Propose ensuite de réessayer.

    def repondre(self, choix: str) -> None:  # Accepte une seule réponse pour la question affichée.
        if self.phase != "question":  # Refuse les doubles clics et les réponses hors question.
            return  # Ne compte pas une deuxième réponse.
        duree = perf_counter() - self.debut  # Mesure uniquement le temps de réflexion.
        self.phase = "sauvegarde"  # Empêche de rejouer avant la fin de l’enregistrement.
        score = calculer_score(choix == self.bonne_race, duree)  # Applique le barème existant.
        for bouton in self.boutons:  # Parcourt les choix visibles.
            bouton.config(state="disabled")  # Bloque une seconde réponse.
        correction = "Bonne réponse !" if choix == self.bonne_race else f"Mauvaise réponse : tu as choisi {choix}."  # Explique le résultat.
        self.resume = f"{correction} Race attendue : {self.bonne_race}.\nTemps : {duree:.2f} s — Score : {score} points."  # Prépare le bilan de la question.
        self.resultat.config(text=self.resume, fg="#22613c" if score else "#a52a2a")  # Affiche immédiatement la correction.
        self.etat.config(text="Sauvegarde du résultat…")  # Signale le traitement en cours.
        Thread(target=self.enregistrer, args=(self.bonne_race, choix, duree, score), daemon=True).start()  # Envoie une copie des valeurs propres à cette question.

    def enregistrer(self, race: str, choix: str, duree: float, score: int) -> None:  # Sauvegarde sans accéder aux composants graphiques.
        confirmations = []  # Sépare les résultats de sauvegarde locale et distante.
        record = None  # Ne suppose pas que le serveur a répondu.
        try:  # Tente de conserver le résultat localement.
            sauvegarder_score(race, choix, duree, score)  # Ajoute une seule ligne CSV.
            confirmations.append("Score sauvegardé dans scores_dog_guesser.csv.")  # Confirme l’écriture locale.
        except OSError:  # Traite une écriture impossible.
            confirmations.append("Échec de la sauvegarde CSV locale.")  # Signale cette erreur indépendamment du serveur.
        try:  # Tente ensuite l’envoi du score.
            record = envoyer_score("Michel Jazeron", score)  # Récupère le record confirmé par le serveur.
            confirmations.append("Record sauvegardé sur le serveur.")  # Confirme l’enregistrement distant.
        except (requests.exceptions.RequestException, ValueError, KeyError):  # Traite une erreur de communication.
            confirmations.append("Serveur indisponible : sauvegarde distante non confirmée.")  # N’annonce pas une réussite non confirmée.
        self.messages.put(("sauvegarde", (record, confirmations)))  # Déclenche la fin du traitement graphique.

    def traiter(self) -> None:  # Centralise les modifications graphiques dans le fil principal.
        try:  # Traite tous les événements HTTP déjà disponibles.
            while True:  # Vide la file sans attendre de nouvelles données.
                type_message, valeur = self.messages.get_nowait()  # Récupère le prochain événement.
                if type_message == "record":  # Met à jour le record personnel.
                    self.record = valeur  # Mémorise la valeur confirmée.
                    self.personnel.config(text=f"Record de Michel Jazeron : {valeur} points")  # Actualise le texte.
                elif type_message == "record_indisponible":  # Signale une lecture impossible.
                    self.record = None  # Évite une comparaison avec une valeur périmée.
                    self.personnel.config(text="Record personnel indisponible — jeu local possible.")  # Informe le joueur.
                elif type_message == "question":  # Présente une question entièrement téléchargée.
                    self.bonne_race, propositions, self.photo_source = valeur  # Remplace les données de la question précédente.
                    self.numero += 1  # Compte cette nouvelle question.
                    self.adapter()  # Affiche la photo aux dimensions disponibles.
                    for bouton, race in zip(self.boutons, propositions):  # Associe chaque bouton à sa propre réponse.
                        bouton.config(text=race, command=lambda choix=race: self.repondre(choix), state="normal")  # Active les réponses.
                    self.etat.config(text=f"Question {self.numero} — à toi de jouer !")  # Annonce le début de la question.
                    self.fenetre.update_idletasks()  # Termine la mise en page avant de démarrer le chronomètre.
                    self.debut = perf_counter()  # Exclut le téléchargement et la préparation du temps mesuré.
                    self.phase = "question"  # Autorise maintenant la réponse.
                    self.rejouer.config(text="Réponds pour rejouer", state="disabled")  # Invite à répondre avant de commencer une nouvelle question.
                elif type_message == "erreur":  # Permet de récupérer après un échec de chargement.
                    self.etat.config(text=valeur, fg="#a52a2a")  # Affiche la cause.
                    self.phase = "repos"  # Autorise une nouvelle tentative.
                    self.rejouer.config(state="normal", text="Réessayer")  # Fournit une action de récupération.
                elif type_message == "sauvegarde":  # Termine une question après les deux sauvegardes.
                    record, confirmations = valeur  # Récupère les confirmations obtenues.
                    if record is not None:  # Utilise uniquement un résultat serveur confirmé.
                        if self.record is not None and record > self.record:  # Détecte une progression connue.
                            confirmations.append("Nouveau record personnel, Michel !")  # Annonce le record battu.
                        self.record = record  # Mémorise le record pour la suite.
                        self.personnel.config(text=f"Record de Michel Jazeron : {record} points")  # Affiche la valeur sauvegardée.
                    self.resultat.config(text=self.resume + "\n" + "\n".join(confirmations))  # Affiche le bilan complet.
                    self.etat.config(text="Question terminée.")  # Indique la fin des traitements.
                    self.phase = "repos"  # Autorise la question suivante.
                    self.rejouer.config(state="normal", text="Rejouer")  # Réactive le bouton de nouvelle partie.
        except Empty:  # Détecte la fin des événements en attente.
            pass  # Rend la main à l’interface.
        try:  # Traite séparément les notifications WebSocket.
            while True:  # Parcourt les notifications reçues.
                donnees = self.records.get_nowait()  # Lit sans bloquer.
                if "erreur" in donnees:  # Signale une perte de connexion.
                    self.global_.config(text=donnees["erreur"], fg="#a52a2a")  # Indique que le record global n’est plus actualisé.
                else:  # Affiche le record et les éventuels ex æquo.
                    noms = ", ".join(donnees["joueurs"]) or "Aucun joueur"  # Prépare les détenteurs.
                    self.global_.config(text=f"Record de tous les temps : {donnees['record']} points\nDétenu par : {noms}", fg="#643a87")  # Actualise le record global.
        except Empty:  # Détecte une file vide.
            pass  # Termine la consultation.
        self.fenetre.after(50, self.traiter)  # Programme le prochain passage sans attente active.


if __name__ == "__main__":  # Lance l’application uniquement en exécution directe.
    jeu = Jeu()  # Prépare la fenêtre et commence le chargement.
    jeu.fenetre.mainloop()  # Traite les événements jusqu’à la fermeture du jeu.
