"""La commande `moteur`, lancée depuis la racine d'un dépôt de parcours.

    moteur --version
    moteur construire     le site statique        (étape M1)
    moteur verifier       prérequis, clés stables (étape M2)
    moteur paquet         le paquet plateforme    (étape M3)
    moteur pdf            les PDF                 (étape M5)

À l'étape M0, seules l'aide et la version fonctionnent : chaque sous-commande annonce l'étape
qui la livrera. argparse (bibliothèque standard) suffit : pas de dépendance à installer.
"""
import argparse
import sys

from . import __version__

# Sous-commande → (aide affichée, étape du plan qui la livre).
COMMANDES = {
    "construire": ("construit le site statique du parcours", "M1"),
    "verifier": ("vérifie prérequis, clés stables, liens et vidéos", "M2"),
    "paquet": ("produit le paquet pour la plateforme (format 1)", "M3"),
    "pdf": ("produit les PDF au style maison", "M5"),
}

# Codes de sortie, pour que les scripts et la CI sachent ce qui s'est passé.
OK = 0
PAS_ENCORE = 3


def analyseur():
    p = argparse.ArgumentParser(
        prog="moteur",
        description="Moteur de contenu des parcours MathNexus.",
    )
    p.add_argument("--version", action="version", version=f"mathnexus-moteur {__version__}")
    sous = p.add_subparsers(dest="commande", metavar="commande")
    for nom, (aide, _etape) in COMMANDES.items():
        sous.add_parser(nom, help=aide, description=aide)
    return p


def principal(arguments=None):
    """Point d'entrée de la commande. Renvoie le code de sortie (utile dans les tests)."""
    args = analyseur().parse_args(arguments)
    if args.commande is None:
        analyseur().print_help()
        return OK
    _aide, etape = COMMANDES[args.commande]
    print(f"« moteur {args.commande} » n'est pas encore disponible : il arrive à l'étape {etape}.",
          file=sys.stderr)
    return PAS_ENCORE


if __name__ == "__main__":
    sys.exit(principal())
