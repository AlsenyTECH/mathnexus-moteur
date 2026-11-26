"""Le registre d'un parcours : Parcours > Parties > Étapes, dans l'ordre où on les apprend.

Un dépôt de parcours écrit ses parties dans `contenu/registre.py` :

    from moteur.registre import Etape as E, Partie

    PARTIES = [
        Partie(0, "Pourquoi la complexité", "Résumé de la partie.", [
            E("m0-deux-algos", "Deux algorithmes, un même problème", 25, "Objectif…"),
            E("m0-attaque", "Ce que coûte une attaque", 25, "Objectif…", ["m0-deux-algos"]),
        ]),
    ]

Le moteur en fait un `Parcours`, qui indexe les étapes par identifiant, les numérote (« 3.3 »)
et vérifie les prérequis. Les statuts (brouillon → vérifié → publié) arrivent à l'étape M2.
"""


class Etape:
    """Une étape : ce qu'on doit savoir faire à la fin, et d'où l'on part.

    ident     identifiant stable (« m3-insertion ») : il deviendra la clé de l'étape sur la plateforme
    minutes   durée prévue
    objectif  « ce qu'on doit savoir faire » à la fin de l'étape
    prereq    identifiants des étapes à avoir faites avant
    examen    question d'annale que l'étape prépare, s'il y en a
    cours     partie correspondante du cours de référence, s'il y en a
    """

    def __init__(self, ident, titre, minutes, objectif, prereq=(), examen=None, cours=None):
        self.id = ident
        self.titre = titre
        self.minutes = minutes
        self.objectif = objectif
        self.prereq = list(prereq)
        self.examen = examen
        self.cours = cours
        self.corps = None  # le cours rédigé (un bloc), rempli par le moteur depuis contenu/

    def __repr__(self):
        return f"Etape({self.id!r})"


class Partie:
    """Une partie du parcours (un « module » pour Complexité, un « chapitre » ailleurs)."""

    def __init__(self, num, titre, resume, etapes):
        self.num = num
        self.titre = titre
        self.resume = resume
        self.etapes = list(etapes)
        self.fichier = None  # nom de la page, fixé par le Parcours selon son motif

    def __repr__(self):
        return f"Partie({self.num!r}, {self.titre!r})"


class Parcours:
    """L'ensemble des parties, avec l'index des étapes.

    motif_fichier  nom de la page d'une partie, où {num} est remplacé par son numéro
    """

    def __init__(self, parties, motif_fichier="module-{num}.html"):
        self.parties = list(parties)
        self.index = {}  # identifiant → (étape, partie) ; en cas de doublon, verifier() le signale
        for p in self.parties:
            p.fichier = motif_fichier.format(num=p.num)
            for e in p.etapes:
                self.index.setdefault(e.id, (e, p))

    def etapes(self):
        """Toutes les étapes, dans l'ordre du parcours."""
        return [e for p in self.parties for e in p.etapes]

    def etape(self, ident):
        return self.index[ident][0]

    def partie_de(self, ident):
        return self.index[ident][1]

    def numero(self, ident):
        """« 3.3 » : numéro de la partie, puis rang de l'étape dans la partie (à partir de 1)."""
        e, p = self.index[ident]
        return "%d.%d" % (p.num, p.etapes.index(e) + 1)

    def suites(self, ident):
        """Les étapes qui citent `ident` dans leurs prérequis, dans l'ordre du parcours."""
        return [e for e in self.etapes() if ident in e.prereq]

    def verifier(self):
        """Liste des problèmes : identifiant en double, prérequis inconnu, prérequis qui vient après.

        Une liste vide veut dire que le registre est cohérent.
        """
        ordre = [e.id for e in self.etapes()]
        pbs = []
        vus = set()
        for eid in ordre:
            if eid in vus:
                pbs.append("identifiant d'étape en double : %s" % eid)
            vus.add(eid)
        for i, e in enumerate(self.etapes()):
            for p in e.prereq:
                if p not in self.index:
                    pbs.append("%s : prérequis inconnu %s" % (e.id, p))
                elif ordre.index(p) >= i:
                    pbs.append("%s : le prérequis %s vient après" % (e.id, p))
        return pbs
