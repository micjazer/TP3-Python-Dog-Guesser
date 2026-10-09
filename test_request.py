# Auteur : Michel Jazeron — michel.jazeron@gmail.com
# TP n°3 : Communiquer à travers le réseau.
# Partie 0 — Question 2 : compter les races principales de chiens.

import requests  # Importe la bibliothèque permettant d’effectuer des requêtes HTTP.
import webbrowser  # Importe le module standard permettant d’ouvrir une adresse dans le navigateur.

def display_random_dog() -> None:  # Affiche une image aléatoire de chien dans le navigateur.
    url: str = "https://dog.ceo/api/breeds/image/random"  # Définit le point d’accès fournissant une image aléatoire.
    reponse = requests.get(url, timeout=10)  # Envoie une requête GET avec un délai d’attente réseau de dix secondes.
    reponse.raise_for_status()  # Déclenche une exception en cas d’erreur HTTP.
    donnees = reponse.json()  # Convertit la réponse JSON en dictionnaire Python.
    if donnees.get("status") != "success":  # Vérifie que l’API annonce une réussite.
        raise ValueError("L’API n’a pas confirmé la récupération de l’image.")  # Signale un échec annoncé par l’API.
    adresse_image = donnees.get("message")  # Récupère l’adresse de l’image.
    if not isinstance(adresse_image, str) or not adresse_image.startswith("https://"):  # Vérifie que la réponse contient une adresse HTTPS.
        raise ValueError("L’adresse de l’image est absente ou incorrecte.")  # Signale une adresse inutilisable.
    print(f"Michel, adresse de l’image : {adresse_image}")  # Affiche l’adresse pour faciliter la vérification.
    ouverture: bool = webbrowser.open(adresse_image, new=2)  # Demande l’ouverture de l’image dans un nouvel onglet.
    if not ouverture:  # Vérifie si le navigateur n’a pas pu être lancé.
        print("Michel, ouvre manuellement l’adresse affichée dans ton navigateur.")  # Indique comment afficher l’image autrement.

def count_num_breeds() -> int:  # Définit une fonction sans paramètre qui renvoie un nombre entier.
    url: str = "https://dog.ceo/api/breeds/list/all"  # Indique l’adresse de l’API fournissant les races.
    reponse = requests.get(url, timeout=10)  # Envoie une requête GET avec un délai d’attente réseau de dix secondes.
    reponse.raise_for_status()  # Déclenche une exception si le serveur renvoie une erreur HTTP.
    donnees = reponse.json()  # Convertit la réponse JSON en données Python.
    if donnees.get("status") != "success":  # Vérifie que l’API annonce une réussite.
        raise ValueError("L’API n’a pas confirmé la réussite de la demande.")  # Signale une réponse applicative incorrecte.
    races = donnees.get("message")  # Récupère le dictionnaire des races principales.
    if not isinstance(races, dict):  # Vérifie que les races sont bien présentées sous forme de dictionnaire.
        raise ValueError("La réponse ne contient pas le dictionnaire des races attendu.")  # Signale un format inattendu.
    return len(races)  # Renvoie le nombre de clés du dictionnaire, donc le nombre de races principales.

if __name__ == "__main__":  # Exécute les exemples uniquement lorsque le script est lancé directement.
    try:  # Tente de compter les races pour la question 2.
        nombre: int = count_num_breeds()  # Récupère le nombre de races principales.
        print(f"Michel, nombre de races principales de chiens : {nombre}")  # Affiche le résultat du comptage.
    except requests.exceptions.RequestException as erreur:  # Intercepte une erreur de requête.
        print(f"Michel, la requête de comptage a échoué : {erreur}")  # Explique l’échec du comptage.
    except ValueError as erreur:  # Intercepte une réponse invalide.
        print(f"Michel, la réponse du comptage est invalide : {erreur}")  # Affiche le problème rencontré.

    try:  # Tente d’afficher une image pour la question 3.
        display_random_dog()  # Récupère l’adresse d’une image aléatoire et l’ouvre dans le navigateur.
    except requests.exceptions.RequestException as erreur:  # Intercepte une erreur de requête.
        print(f"Michel, la récupération de l’image a échoué : {erreur}")  # Explique l’échec de la récupération.
    except ValueError as erreur:  # Intercepte une réponse invalide.
        print(f"Michel, la réponse concernant l’image est invalide : {erreur}")  # Affiche le problème rencontré.
