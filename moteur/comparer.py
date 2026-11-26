"""Comparer deux sites générés, octet par octet.

    moteur comparer ANCIEN NOUVEAU

Sert de preuve quand le générateur change sans que le contenu change : migration d'un parcours
vers le moteur (M1), montée de version du moteur dans un dépôt de parcours. Tout compte :
pages, CSS, JS, polices, Pyodide, vidéos, dossiers vides. Une seule différence suffit à échouer.
"""
import os
from dataclasses import dataclass, field


@dataclass
class Ecarts:
    manquants: list = field(default_factory=list)   # dans l'ancien, absents du nouveau
    en_trop: list = field(default_factory=list)     # dans le nouveau, absents de l'ancien
    differents: list = field(default_factory=list)  # présents des deux côtés, contenu différent

    def identiques(self):
        return not (self.manquants or self.en_trop or self.differents)

    def rapport(self):
        if self.identiques():
            return "Sites identiques."
        lignes = []
        for titre, chemins in (("Manquants dans le nouveau", self.manquants),
                               ("En trop dans le nouveau", self.en_trop),
                               ("Contenu différent", self.differents)):
            if chemins:
                lignes.append("%s (%d) :" % (titre, len(chemins)))
                lignes += ["  - " + c for c in chemins]
        return "\n".join(lignes)


def inventaire(racine):
    """Chemins relatifs (séparés par « / ») des fichiers et des dossiers sous `racine`.

    Les dossiers finissent par « / », pour qu'un dossier vide compte aussi.
    """
    chemins = set()
    for dossier, sous, fichiers in os.walk(racine):
        rel = os.path.relpath(dossier, racine)
        base = "" if rel == "." else rel.replace(os.sep, "/") + "/"
        for d in sous:
            chemins.add(base + d + "/")
        for f in fichiers:
            chemins.add(base + f)
    return chemins


def memes_octets(a, b, bloc=1 << 20):
    """Vrai si les deux fichiers ont exactement les mêmes octets.

    On lit vraiment les deux fichiers, par morceaux d'un Mo. Pas de filecmp : il garde en cache le
    résultat selon la taille et la date de modification, et sous Windows un fichier réécrit dans la même
    seconde avec la même taille paraîtrait inchangé.
    """
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            ma, mb = fa.read(bloc), fb.read(bloc)
            if ma != mb:
                return False
            if not ma:
                return True


def comparer(ancien, nouveau):
    for d in (ancien, nouveau):
        if not os.path.isdir(d):
            raise FileNotFoundError("dossier introuvable : %s" % d)
    a, b = inventaire(ancien), inventaire(nouveau)
    ecarts = Ecarts(manquants=sorted(a - b), en_trop=sorted(b - a))
    for c in sorted(a & b):
        if c.endswith("/"):
            continue
        if not memes_octets(os.path.join(ancien, c), os.path.join(nouveau, c)):
            ecarts.differents.append(c)
    return ecarts
