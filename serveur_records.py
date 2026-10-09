# Auteur : Michel Jazeron — michel.jazeron@gmail.com.
# TP3 : serveur HTTP de sauvegarde des records du jeu Dog Guesser.

import json  # Importe les outils de lecture et d’écriture du format JSON.
import asyncio  # Importe les outils permettant d’attendre des opérations réseau sans bloquer tout le serveur.
from fastapi import WebSocket, WebSocketDisconnect  # Importe la gestion des connexions WebSocket et de leurs déconnexions.
from pathlib import Path  # Importe la gestion des chemins de fichiers.
from threading import Lock  # Importe un verrou pour protéger les accès simultanés au fichier.
from typing import Literal  # Permet de limiter les scores aux valeurs prévues par le barème.
from fastapi import FastAPI, HTTPException  # Importe la création de l’API et la gestion des erreurs HTTP.
from pydantic import BaseModel, Field  # Importe les outils de validation des données reçues.

app = FastAPI(title="Records Dog Guesser — Michel Jazeron")  # Crée l’application serveur.
FICHIER_RECORDS = Path(__file__).resolve().parent / "records.json"  # Définit le fichier géré par le serveur.
verrou = Lock()  # Crée un verrou partagé par les opérations de lecture et de modification.
connexions: set[WebSocket] = set()  # Conserve les connexions des interfaces actuellement abonnées aux records.
verrou_diffusion = asyncio.Lock()  # Garantit que les actualisations sont diffusées dans leur ordre de traitement.

class ScoreRecu(BaseModel):  # Définit les informations attendues lors de l’envoi d’un score.
    joueur: str = Field(min_length=1, max_length=100)  # Exige un nom de joueur non vide de cent caractères maximum.
    score: Literal[0, 100, 125, 150]  # Accepte uniquement les scores possibles selon notre barème.


def charger_records() -> dict[str, int]:  # Lit les records conservés sur le disque du serveur.
    try:  # Tente de lire le fichier existant.
        with open(FICHIER_RECORDS, "r", encoding="utf-8") as fichier:  # Ouvre le fichier et garantit sa fermeture.
            records = json.load(fichier)  # Convertit le contenu JSON en objet Python.
    except FileNotFoundError:  # Traite le premier démarrage sans fichier de records.
        return {}  # Renvoie un dictionnaire vide.
    if not isinstance(records, dict):  # Vérifie que le fichier contient un dictionnaire.
        raise ValueError("Le fichier des records doit contenir un dictionnaire.")  # Signale un format incorrect.
    for joueur, score in records.items():  # Vérifie les valeurs chargées depuis le disque.
        if not isinstance(joueur, str) or type(score) is not int or score not in (0, 100, 125, 150):  # Contrôle les noms et les scores.
            raise ValueError("Le fichier contient un record invalide.")  # Refuse de modifier un fichier incohérent.
    return records  # Renvoie les records validés.


def enregistrer_records(records: dict[str, int]) -> None:  # Sauvegarde les records dans le fichier du serveur.
    temporaire = FICHIER_RECORDS.with_suffix(".tmp")  # Prépare un fichier temporaire dans le même dossier.
    with open(temporaire, "w", encoding="utf-8") as fichier:  # Ouvre le fichier temporaire en écriture.
        json.dump(records, fichier, ensure_ascii=False, indent=4)  # Écrit les records dans un format lisible.
    temporaire.replace(FICHIER_RECORDS)  # Remplace le fichier des records une fois l’écriture terminée.


@app.get("/record")  # Associe une requête HTTP GET à la consultation d’un record.
def obtenir_record(joueur: str) -> dict[str, int]:  # Renvoie le record du joueur demandé.
    try:  # Tente de lire les records.
        with verrou:  # Empêche une modification simultanée pendant la lecture.
            records = charger_records()  # Charge les records depuis le fichier.
        return {"record": records.get(joueur, 0)}  # Renvoie zéro si le joueur n’a pas encore de record.
    except (OSError, ValueError) as erreur:  # Intercepte une erreur de fichier ou de contenu.
        raise HTTPException(status_code=500, detail="Impossible de lire les records.") from erreur  # Signale une erreur du serveur.

def calculer_record_global(records: dict[str, int]) -> dict:  # Construit le record de tous les joueurs et la liste de ses détenteurs.
    meilleur = max(records.values(), default=0)  # Recherche le meilleur score ou utilise zéro si le fichier est vide.
    joueurs = sorted(joueur for joueur, score in records.items() if score == meilleur)  # Liste les joueurs ayant ce score par ordre alphabétique.
    return {"record": meilleur, "joueurs": joueurs}  # Renvoie les informations à afficher dans les interfaces.


async def diffuser_record(donnees: dict) -> None:  # Envoie le record global à toutes les interfaces connectées.
    for connexion in list(connexions):  # Parcourt une copie des connexions pour permettre leur suppression.
        try:  # Tente d’envoyer le nouveau record.
            await asyncio.wait_for(connexion.send_json(donnees), timeout=2)  # Envoie le JSON en limitant l’attente à deux secondes.
        except (WebSocketDisconnect, OSError, RuntimeError, TimeoutError):  # Détecte une connexion fermée ou devenue inutilisable.
            connexions.discard(connexion)  # Retire la connexion de la liste des destinataires.


@app.websocket("/ws/records")  # Définit l’adresse du canal WebSocket des records.
async def suivre_records(connexion: WebSocket) -> None:  # Gère l’abonnement d’une interface aux changements de record.
    await connexion.accept()  # Accepte la connexion demandée par le jeu.
    try:  # Gère la connexion jusqu’à sa fermeture.
        async with verrou_diffusion:  # Évite qu’une actualisation s’intercale pendant l’envoi du record initial.
            with verrou:  # Protège la lecture du fichier partagé.
                donnees = calculer_record_global(charger_records())  # Calcule le record actuel à partir du fichier du serveur.
            await asyncio.wait_for(connexion.send_json(donnees), timeout=2)  # Transmet immédiatement le record au nouveau client.
            connexions.add(connexion)  # Inscrit le client aux prochaines actualisations.
        while True:  # Maintient la connexion ouverte.
            await connexion.receive_text()  # Attend un éventuel message ou détecte la déconnexion du client.
    except (WebSocketDisconnect, OSError, RuntimeError, TimeoutError, ValueError):  # Traite une déconnexion ou une erreur.
        pass  # Termine la gestion de cette connexion.
    finally:  # Effectue le nettoyage quelle que soit la cause de sortie.
        connexions.discard(connexion)  # Supprime le client de la liste des abonnés.

@app.post("/score")  # Définit la route HTTP utilisée pour transmettre un score.
async def recevoir_score(resultat: ScoreRecu) -> dict[str, int]:  # Sauvegarde le record personnel et diffuse les changements du record global.
    async with verrou_diffusion:  # Traite les mises à jour et leurs notifications dans le même ordre.
        try:  # Tente de modifier les records sauvegardés.
            with verrou:  # Protège la lecture et l’écriture du fichier.
                records = charger_records()  # Charge les records existants.
                ancien_global = calculer_record_global(records)  # Mémorise le record global avant la modification.
                record = max(records.get(resultat.joueur, 0), resultat.score)  # Conserve le meilleur score personnel.
                records[resultat.joueur] = record  # Actualise le record du joueur.
                enregistrer_records(records)  # Sauvegarde le fichier avant de notifier les clients.
                nouveau_global = calculer_record_global(records)  # Calcule le record global après la sauvegarde.
        except (OSError, ValueError) as erreur:  # Intercepte une erreur de fichier.
            raise HTTPException(status_code=500, detail="Impossible de sauvegarder le record.") from erreur  # Signale l’échec au client.
        if nouveau_global != ancien_global:  # Vérifie si le score global ou ses détenteurs ont changé.
            await diffuser_record(nouveau_global)  # Envoie les nouvelles informations aux interfaces ouvertes.
        return {"record": record}  # Confirme le record personnel au client ayant envoyé le score.
