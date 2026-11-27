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
et vérifie les prérequis.

Chaque étape a un statut (étape M2 du plan) :

    brouillon   en cours d'écriture (par défaut) : le site affiche sa fiche
    verifie     cours relu, nombres vérifiés : prête à sortir, le site affiche encore sa fiche
    publie      le cours sort ; sa clé entre dans cles.lock et ne doit plus jamais disparaître

    E("m3-insertion", "Le tri par insertion", 50, "Objectif…", ["m3-boucles"], statut="publie")

Et un niveau d'accès sur la plateforme (étape M3), « inscrit » par défaut :

    E("m0-deux-algos", "Deux algorithmes", 25, "Objectif…", statut="publie", acces="public")
"""

BROUILLON = "brouillon"
VERIFIE = "verifie"
PUBLIE = "publie"
STATUTS = (BROUILLON, VERIFIE, PUBLIE)  # dans l'ordre de la vie d'une étape

# Niveaux d'accès sur la plateforme (format de paquet 1) : public = vitrine sans compte,
# inscrit = tout élève validé d'une classe rattachée (par défaut), premium = offre payante.
ACCES = ("public", "inscrit", "premium")


class ErreurStatut(ValueError):
    """Statut ou accès inconnu : la faute de frappe est signalée dès la lecture du registre."""


class Etape:
    """Une étape : ce qu'on doit savoir faire à la fin, et d'où l'on part.

    ident     identifiant stable (« m3-insertion ») : il deviendra la clé de l'étape sur la plateforme
    minutes   durée prévue
    objectif  « ce qu'on doit savoir faire » à la fin de l'étape
    prereq    identifiants des étapes à avoir faites avant
    examen    question d'annale que l'étape prépare, s'il y en a
    cours     partie correspondante du cours de référence, s'il y en a
    statut    brouillon (par défaut), verifie ou publie ; à donner par son nom : statut="publie"
    acces     sur la plateforme : public, inscrit (par défaut) ou premium ; par son nom : acces="public"
    """

    def __init__(self, ident, titre, minutes, objectif, prereq=(), examen=None, cours=None, *,
                 statut=BROUILLON, acces="inscrit"):
        if statut not in STATUTS:
            raise ErreurStatut("étape %s : statut inconnu %r (attendu : %s)"
                               % (ident, statut, ", ".join(STATUTS)))
        if acces not in ACCES:
            raise ErreurStatut("étape %s : accès inconnu %r (attendu : %s)"
                               % (ident, acces, ", ".join(ACCES)))
        self.id = ident
        self.titre = titre
        self.minutes = minutes
        self.objectif = objectif
        self.prereq = list(prereq)
        self.examen = examen
        self.cours = cours
        self.statut = statut
        self.acces = acces
        self.corps = None  # le cours rédigé (un bloc), rempli par le moteur depuis contenu/

    @property
    def redigee(self):
        """Vrai si le cours de l'étape est écrit ; sinon la page affiche sa fiche."""
        return self.corps is not None and self.corps != ""

    @property
    def publiee(self):
        """Vrai si le cours de l'étape sort sur le site (et, en M3, dans le paquet)."""
        return self.statut == PUBLIE

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

    def verifier_statuts(self):
        """Liste des problèmes de statut, une fois le cours chargé.

        Une étape vérifiée ou publiée doit avoir son cours écrit : on ne vérifie pas, et on ne
        publie pas, une page vide. Un brouillon peut avoir un cours (en cours d'écriture) ou non.
        """
        return ["%s : statut %s, mais son cours n'est pas écrit" % (e.id, e.statut)
                for e in self.etapes() if e.statut != BROUILLON and not e.redigee]
