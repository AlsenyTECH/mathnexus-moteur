"""Le contrat avec la plateforme : moteur/controle.py doit rester la copie exacte de son paquet.py.

Le format des paquets appartient à la plateforme (`backend/contenus/FORMAT_PAQUET.md` et `paquet.py`).
Le moteur en garde une copie octet pour octet, `moteur/controle.py`, et passe chaque paquet construit
dans sa fonction `lire_paquet` : si la plateforme le refuserait, la construction échoue.

Pour que la copie ne dérive pas sans qu'on le voie :

- un test vérifie que l'empreinte SHA-256 de controle.py est bien EMPREINTE ci-dessous ;
- la CI lance `python -m moteur.contrat`, qui télécharge paquet.py depuis la branche main de la
  plateforme et échoue si son empreinte a changé. Quand cela arrive : relire le changement dans la
  plateforme, recopier le fichier, mettre à jour EMPREINTE et COMMIT, adapter le moteur, nouvelle version.

    python -m moteur.contrat          code 0 : identique ; 1 : la plateforme a changé ; 2 : téléchargement impossible
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

DEPOT = "AlsenyTECH/mathnexus-plateforme"
CHEMIN = "backend/contenus/paquet.py"
COMMIT = "30be916d71650db0ec8a5ae689b38ce1dae2b3ec"  # main de la plateforme au moment de la copie
EMPREINTE = "0d48e09c52bcc814905e07a383d29393f97217823cff0a40a88c933a17b3f3fe"
URL = "https://raw.githubusercontent.com/%s/main/%s" % (DEPOT, CHEMIN)

FICHIER_CONTROLE = Path(__file__).with_name("controle.py")

IDENTIQUE, CHANGE, INJOIGNABLE = 0, 1, 2


def empreinte(donnees: bytes) -> str:
    return hashlib.sha256(donnees).hexdigest()


def empreinte_controle() -> str:
    """Empreinte de la copie installée avec le moteur."""
    return empreinte(FICHIER_CONTROLE.read_bytes())


def principal(url=URL):
    try:
        with urllib.request.urlopen(url, timeout=30) as reponse:
            distant = reponse.read()
    except OSError as err:
        print("moteur.contrat : impossible de télécharger %s (%s)" % (url, err), file=sys.stderr)
        return INJOIGNABLE
    if empreinte(distant) == EMPREINTE:
        print("Contrat respecté : controle.py est identique au paquet.py de la plateforme (main).")
        return IDENTIQUE
    print("La plateforme a changé %s depuis la copie (commit %s).\n"
          "Relire le changement, recopier le fichier dans moteur/controle.py, mettre à jour EMPREINTE et COMMIT\n"
          "dans moteur/contrat.py, puis adapter le moteur." % (CHEMIN, COMMIT[:7]), file=sys.stderr)
    return CHANGE


if __name__ == "__main__":
    sys.exit(principal())
