"""Le fichier cles.lock d'un dépôt de parcours : les clés des étapes publiées.

Une étape publiée a une clé (son identifiant, « m3-insertion »). Sur la plateforme, la progression
des élèves est accrochée à cette clé : si elle disparaît ou change de nom, l'élève perd ce qu'il a fait.
cles.lock garde la liste de toutes les clés déjà publiées, et la construction refuse :

    - une clé de la liste qui n'est plus dans le registre (étape supprimée ou renommée) ;
    - une étape publiée qui n'est pas dans la liste (on doit l'y ajouter, en le sachant) ;
    - des étapes publiées sans fichier cles.lock.

Le fichier est du texte : une clé par ligne, triées, lignes « # » pour les commentaires.

    # cles.lock — clés des étapes publiées de ce parcours.
    m0-attaque
    m3-insertion

Seule la commande « moteur verifier --maj-cles » l'écrit, et elle ne fait qu'ajouter.
Retirer une clé se fait à la main : un geste volontaire, visible dans la demande de fusion.
Dépublier une étape reste permis : sa clé reste dans la liste, donc l'étape reste dans le registre.
"""
import os
import re

NOM_FICHIER = "cles.lock"

# Le format des clés imposé par la plateforme (FORMAT_PAQUET.md, format 1). Une clé publiée est
# définitive : autant refuser dès la publication une clé que la plateforme refuserait.
FORMAT_CLE = re.compile(r"^[a-z0-9][a-z0-9-]{0,59}$")

ENTETE = """\
# cles.lock — clés des étapes publiées de ce parcours.
# Mis à jour par « moteur verifier --maj-cles », qui ajoute seulement.
# Une clé listée ici ne doit jamais disparaître du registre ni changer de nom :
# la progression des élèves y est accrochée. Retirer une clé se fait à la main, en le sachant.
"""

COMMANDE_MAJ = "moteur verifier --maj-cles"


class ErreurCles(ValueError):
    """cles.lock illisible (ligne qui n'est pas une clé)."""


def chemin(racine):
    return os.path.join(racine, NOM_FICHIER)


def lire(racine):
    """L'ensemble des clés de cles.lock, ou None si le fichier n'existe pas."""
    try:
        with open(chemin(racine), encoding="utf-8") as f:
            lignes = f.read().splitlines()
    except FileNotFoundError:
        return None
    cles = set()
    for n, ligne in enumerate(lignes, 1):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        if not FORMAT_CLE.match(ligne):
            raise ErreurCles("%s, ligne %d : %r n'est pas une clé (minuscules, chiffres et -, 60 au plus)"
                             % (NOM_FICHIER, n, ligne))
        cles.add(ligne)
    return cles


def ecrire(racine, cles):
    """Écrit cles.lock : l'entête, puis les clés triées.

    newline="\\n" : même fichier, octet pour octet, sous Windows et sous Linux.
    """
    with open(chemin(racine), "w", encoding="utf-8", newline="\n") as f:
        f.write(ENTETE)
        for c in sorted(cles):
            f.write(c + "\n")


def publiees(parcours):
    return [e for e in parcours.etapes() if e.publiee]


def a_ajouter(parcours, cles):
    """Les clés publiées qui manquent à cles.lock, dans l'ordre du parcours."""
    cles = cles or set()
    return [e.id for e in publiees(parcours) if e.id not in cles]


def controler(parcours, cles):
    """Liste des problèmes entre le registre et cles.lock (cles : l'ensemble lu, ou None).

    Une liste vide veut dire que toutes les clés publiées sont en place.
    """
    pbs = []
    for e in publiees(parcours):
        if not FORMAT_CLE.match(e.id):
            pbs.append("%s : cette clé ne peut pas être publiée (minuscules, chiffres et -, 60 au plus, "
                       "format de la plateforme)" % e.id)
    if cles is None:
        if publiees(parcours):
            pbs.append("des étapes sont publiées mais %s n'existe pas : lance « %s »"
                       % (NOM_FICHIER, COMMANDE_MAJ))
        return pbs
    for c in sorted(cles - parcours.index.keys()):
        pbs.append("la clé publiée %s a disparu du registre (étape supprimée ou renommée) : une clé publiée "
                   "ne change jamais, remets l'étape %s dans contenu/registre.py" % (c, c))
    for c in a_ajouter(parcours, cles):
        pbs.append("%s est publiée mais n'est pas dans %s : lance « %s »" % (c, NOM_FICHIER, COMMANDE_MAJ))
    return pbs


def mettre_a_jour(racine, parcours):
    """Ajoute à cles.lock les clés publiées qui manquent, sans rien retirer. Renvoie les clés ajoutées.

    Le fichier n'est pas réécrit s'il n'y a rien à ajouter (pas de changement inutile dans Git).
    """
    cles = lire(racine)
    nouvelles = [c for c in a_ajouter(parcours, cles) if FORMAT_CLE.match(c)]
    if nouvelles:
        ecrire(racine, (cles or set()) | set(nouvelles))
    return nouvelles
