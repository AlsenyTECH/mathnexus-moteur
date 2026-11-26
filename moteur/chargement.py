"""Charger un dépôt de parcours : ses réglages, son registre, son cours, ses pages propres.

    parcours.toml          les réglages (moteur.reglages)
    contenu/registre.py    PARTIES : la liste des parties et de leurs étapes
    contenu/*.py           CORPS[identifiant] = etape(…) : le cours rédigé
    contenu/pages.py       facultatif : pages(site) → {nom de fichier : HTML} (accueil, outils…)

Les fichiers dont le nom commence par « _ » ne sont pas lus comme du cours (aides partagées).
"""
import importlib.util
import itertools
import os
import sys
from dataclasses import dataclass

from . import reglages as _reglages
from .blocs import Bloc
from .registre import Parcours

_compteur = itertools.count()


class ErreurConstruction(Exception):
    """La construction est refusée. `problemes` liste ce qu'il faut corriger."""

    def __init__(self, titre, problemes=()):
        super().__init__(titre)
        self.titre = titre
        self.problemes = list(problemes)

    def __str__(self):
        if not self.problemes:
            return self.titre
        return self.titre + " :\n  - " + "\n  - ".join(self.problemes)


@dataclass
class DepotParcours:
    racine: str
    reglages: object
    parcours: Parcours
    pages: object = None   # fonction pages(site), ou None


def _importer(chemin, groupe):
    """Importe un fichier Python sous un nom privé, pour que deux parcours ne se mélangent pas."""
    nom = "_parcours_%d_%s" % (groupe, os.path.splitext(os.path.basename(chemin))[0])
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        rel = "contenu/" + os.path.basename(chemin)  # même message sous Windows et Linux
        raise ErreurConstruction("Erreur dans %s : %s: %s" % (rel, type(err).__name__, err)) from err
    return module


def charger(racine="."):
    racine = os.path.abspath(racine)
    chemin_toml = os.path.join(racine, "parcours.toml")
    if not os.path.exists(chemin_toml):
        raise ErreurConstruction("Pas de parcours.toml dans %s : lance la commande depuis la racine "
                                 "du dépôt du parcours, ou donne-le avec --dossier." % racine)
    try:
        reglages = _reglages.lire_fichier(chemin_toml)
    except _reglages.ErreurReglages as err:
        raise ErreurConstruction(str(err)) from None

    contenu = os.path.join(racine, "contenu")
    groupe = next(_compteur)
    # Le dossier contenu/ est ajouté au chemin le temps du chargement : un fichier de cours peut
    # importer une aide voisine (from _commun import …).
    sys.path.insert(0, contenu)
    try:
        chemin_registre = os.path.join(contenu, "registre.py")
        if not os.path.exists(chemin_registre):
            raise ErreurConstruction("contenu/registre.py manquant")
        registre = _importer(chemin_registre, groupe)
        if not hasattr(registre, "PARTIES"):
            raise ErreurConstruction("contenu/registre.py doit définir PARTIES (la liste des parties)")
        parcours = Parcours(registre.PARTIES, reglages.fichier_partie)
        pbs = parcours.verifier()
        if pbs:
            raise ErreurConstruction("Registre incohérent", pbs)

        pages = None
        origine = {}
        for nom in sorted(os.listdir(contenu)):
            if not nom.endswith(".py") or nom.startswith("_") or nom == "registre.py":
                continue
            module = _importer(os.path.join(contenu, nom), groupe)
            if nom == "pages.py":
                pages = getattr(module, "pages", None)
                if not callable(pages):
                    raise ErreurConstruction("contenu/pages.py doit définir une fonction pages(site)")
                continue
            for eid, corps in getattr(module, "CORPS", {}).items():
                if eid not in parcours.index:
                    raise ErreurConstruction("contenu/%s : étape inconnue %s" % (nom, eid))
                if eid in origine:
                    raise ErreurConstruction("étape %s rédigée deux fois : contenu/%s et contenu/%s"
                                             % (eid, origine[eid], nom))
                if not isinstance(corps, (str, Bloc)):
                    raise ErreurConstruction("contenu/%s : le cours de %s doit être un bloc ou du HTML, pas %s"
                                             % (nom, eid, type(corps).__name__))
                origine[eid] = nom
                parcours.etape(eid).corps = corps
    finally:
        sys.path.remove(contenu)
    return DepotParcours(racine, reglages, parcours, pages)
