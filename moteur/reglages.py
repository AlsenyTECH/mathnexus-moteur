"""Les réglages d'un parcours, lus dans `parcours.toml` à la racine de son dépôt.

tomllib fait partie de la bibliothèque standard depuis Python 3.11 : pas de dépendance.
Une clé inconnue est refusée : une faute de frappe ne doit pas passer en silence.
Voir tests/exemple/parcours.toml pour un fichier complet et commenté.
"""
import tomllib
from dataclasses import dataclass, field

TEMPS_PAR_DEFAUT = (
    ("Comprendre", "Lis, regarde la vidéo, essaie les exemples."),
    ("Démontrer", "Refais chaque calcul sur une feuille avant d'ouvrir la correction."),
    ("Implémenter", "Code dans la page ; les tests vérifient."),
    ("S'exercer", "Exercices gradués, puis le test de sortie qui valide l'étape."),
)


class ErreurReglages(ValueError):
    pass


@dataclass
class Lien:
    lien: str
    texte: str
    symbole: str = ""


@dataclass
class Reglages:
    # [parcours]
    titre: str
    titre_long: str
    sous_titre: str = ""
    description: str = ""
    auteur: str = "MathNexus"
    annee: int = 2026
    # [site]
    sortie: str = "_site"
    videos: str = "videos"
    prefixe_stockage: str = "parcours"
    icone: str = ""
    message_accueil_vide: str = "Aucune étape validée pour l'instant."
    css: list = field(default_factory=list)
    js: list = field(default_factory=list)
    scripts_partie: list = field(default_factory=lambda: ["site.js", "atelier.js", "mesure.js"])
    barre: list = field(default_factory=list)       # de Lien
    sommaire: list = field(default_factory=list)    # de Lien, ajoutés au sommaire des parties
    # [parties]
    nom_partie: str = "Module"
    demonstratif: str = "ce module"
    complement: str = "du module"
    fichier_partie: str = "module-{num}.html"
    # [gabarit]
    temps: list = field(default_factory=lambda: [list(t) for t in TEMPS_PAR_DEFAUT])
    # [mathjax]
    macros: dict = field(default_factory=dict)

    @property
    def noms_temps(self):
        return [nom for nom, _consigne in self.temps]


# table TOML → { clé TOML : attribut de Reglages }
_TABLES = {
    "parcours": {"titre": "titre", "titre_long": "titre_long", "sous_titre": "sous_titre",
                 "description": "description", "auteur": "auteur", "annee": "annee"},
    "site": {"sortie": "sortie", "videos": "videos", "prefixe_stockage": "prefixe_stockage",
             "icone": "icone", "message_accueil_vide": "message_accueil_vide", "css": "css",
             "js": "js", "scripts_partie": "scripts_partie", "barre": "barre", "sommaire": "sommaire"},
    "parties": {"nom": "nom_partie", "demonstratif": "demonstratif", "complement": "complement",
                "fichier": "fichier_partie"},
    "gabarit": {"temps": "temps"},
    "mathjax": {"macros": "macros"},
}


def _liens(valeur, ou):
    liens = []
    for i, d in enumerate(valeur):
        if not isinstance(d, dict) or not {"lien", "texte"} <= d.keys() or d.keys() - {"lien", "texte", "symbole"}:
            raise ErreurReglages("%s, entrée %d : attendu lien, texte (et symbole facultatif)" % (ou, i + 1))
        liens.append(Lien(**d))
    return liens


def lire(texte, nom="parcours.toml"):
    try:
        donnees = tomllib.loads(texte)
    except tomllib.TOMLDecodeError as err:
        raise ErreurReglages("%s : %s" % (nom, err)) from None
    inconnues = donnees.keys() - _TABLES.keys()
    if inconnues:
        raise ErreurReglages("%s : table inconnue [%s]" % (nom, ", ".join(sorted(inconnues))))
    valeurs = {}
    for table, cles in _TABLES.items():
        contenu = donnees.get(table, {})
        for cle in contenu.keys() - cles.keys():
            raise ErreurReglages("%s : clé inconnue « %s » dans [%s]" % (nom, cle, table))
        for cle, attribut in cles.items():
            if cle in contenu:
                valeurs[attribut] = contenu[cle]
    for obligatoire in ("titre", "titre_long"):
        if obligatoire not in valeurs:
            raise ErreurReglages("%s : [parcours] %s est obligatoire" % (nom, obligatoire))
    for cle in ("barre", "sommaire"):
        if cle in valeurs:
            valeurs[cle] = _liens(valeurs[cle], "%s, [[site.%s]]" % (nom, cle))
    if "temps" in valeurs:
        t = valeurs["temps"]
        if len(t) != 4 or any(not isinstance(x, dict) or set(x) != {"nom", "consigne"} for x in t):
            raise ErreurReglages("%s : [gabarit] temps doit donner 4 temps, chacun avec nom et consigne" % nom)
        valeurs["temps"] = [[x["nom"], x["consigne"]] for x in t]
    if '"' in valeurs.get("icone", ""):
        raise ErreurReglages('%s : [site] icone ne doit pas contenir de guillemet "' % nom)
    if "{num}" not in valeurs.get("fichier_partie", "{num}"):
        raise ErreurReglages("%s : [parties] fichier doit contenir {num}" % nom)
    prefixe = valeurs.get("prefixe_stockage", "parcours")
    if not prefixe.replace("-", "").replace("_", "").isalnum() or not prefixe.isascii():
        raise ErreurReglages("%s : [site] prefixe_stockage : lettres, chiffres, - et _ seulement" % nom)
    return Reglages(**valeurs)


def lire_fichier(chemin):
    with open(chemin, encoding="utf-8") as f:
        return lire(f.read(), str(chemin))
