"""La commande `moteur`, lancée depuis la racine d'un dépôt de parcours.

    moteur --version
    moteur construire     le site statique        (étape M1)
    moteur comparer A B   deux sites, octet par octet (étape M1)
    moteur verifier       tous les contrôles, sans construire (étape M2)
    moteur paquet         le paquet plateforme    (étape M3)
    moteur pdf            les PDF                 (étape M5)

Les sous-commandes pas encore livrées annoncent l'étape qui les livrera.
argparse (bibliothèque standard) suffit : pas de dépendance à installer.
"""
import argparse
import sys

from . import __version__

# Sous-commandes pas encore livrées → (aide affichée, étape du plan qui la livre).
A_VENIR = {
    "paquet": ("produit le paquet pour la plateforme (format 1)", "M3"),
    "pdf": ("produit les PDF au style maison", "M5"),
}

# Codes de sortie, pour que les scripts et la CI sachent ce qui s'est passé.
OK = 0
ECHEC = 1        # construction refusée, sites différents
PAS_ENCORE = 3


def analyseur():
    p = argparse.ArgumentParser(
        prog="moteur",
        description="Moteur de contenu des parcours MathNexus.",
    )
    p.add_argument("--version", action="version", version=f"mathnexus-moteur {__version__}")
    sous = p.add_subparsers(dest="commande", metavar="commande")

    c = sous.add_parser("construire", help="construit le site statique du parcours",
                        description="Construit le site statique du parcours (réglages dans parcours.toml).")
    c.add_argument("--dossier", default=".", help="racine du dépôt du parcours (par défaut : ici)")
    c.add_argument("--sortie", help="dossier du site (par défaut : [site] sortie de parcours.toml)")
    c.add_argument("--brouillons", action="store_true",
                   help="aperçu pour relire : sort aussi le cours des étapes en brouillon ou vérifiées, "
                        "avec un bandeau, dans _apercu/ (à ne jamais publier)")

    c = sous.add_parser("comparer", help="compare deux sites générés, octet par octet",
                        description="Compare deux sites générés, octet par octet. "
                                    "Code de sortie 0 s'ils sont identiques, 1 sinon.")
    c.add_argument("ancien", help="dossier du site de référence")
    c.add_argument("nouveau", help="dossier du site à comparer")

    c = sous.add_parser("verifier", help="contrôle le parcours sans construire (registre, statuts, clés, vidéos, liens)",
                        description="Lance tous les contrôles de la construction sans rien construire. "
                                    "Code de sortie 0 sans erreur (même avec des avertissements), 1 sinon.")
    c.add_argument("--dossier", default=".", help="racine du dépôt du parcours (par défaut : ici)")
    c.add_argument("--maj-cles", action="store_true",
                   help="ajoute à cles.lock les clés des étapes publiées qui manquent (n'en retire jamais)")

    for nom, (aide, _etape) in A_VENIR.items():
        sous.add_parser(nom, help=aide, description=aide)
    return p


def commande_construire(args):
    from .chargement import ErreurConstruction
    from .sorties.site import avancement, construire
    try:
        site, sortie = construire(args.dossier, args.sortie, args.brouillons)
    except ErreurConstruction as err:
        print(str(err), file=sys.stderr)
        return ECHEC
    print(avancement(site, sortie))
    return OK


def commande_comparer(args):
    from .comparer import comparer
    try:
        ecarts = comparer(args.ancien, args.nouveau)
    except FileNotFoundError as err:
        print("moteur comparer : %s" % err, file=sys.stderr)
        return ECHEC
    print(ecarts.rapport())
    return OK if ecarts.identiques() else ECHEC


def commande_verifier(args):
    from . import cles
    from .chargement import ErreurConstruction, charger
    from .sorties.site import Site, rendre_pages
    from .verifier import controler
    try:
        depot = charger(args.dossier)
        if args.maj_cles:
            try:
                ajoutees = cles.mettre_a_jour(depot.racine, depot.parcours)
                print("cles.lock : %s" % ("ajoutée(s) : " + ", ".join(ajoutees) if ajoutees else "rien à ajouter"))
            except cles.ErreurCles:
                pass  # fichier illisible : le contrôle ci-dessous le signale
        site = Site(depot)
        resultat = controler(site, rendre_pages(site))
    except ErreurConstruction as err:
        print("Erreurs (la construction sera refusée) :\n  " + str(err).replace("\n", "\n  "))
        return ECHEC
    etapes = depot.parcours.etapes()
    nb = {st: sum(1 for e in etapes if e.statut == st) for st in ("publie", "verifie", "brouillon")}
    print("moteur verifier : %d étapes (%d publiée(s), %d vérifiée(s), %d brouillon(s))"
          % (len(etapes), nb["publie"], nb["verifie"], nb["brouillon"]))
    print(resultat.rapport())
    return ECHEC if resultat.erreurs else OK


COMMANDES = {"construire": commande_construire, "comparer": commande_comparer, "verifier": commande_verifier}


def principal(arguments=None):
    """Point d'entrée de la commande. Renvoie le code de sortie (utile dans les tests)."""
    p = analyseur()
    args = p.parse_args(arguments)
    if args.commande is None:
        p.print_help()
        return OK
    if args.commande in COMMANDES:
        return COMMANDES[args.commande](args)
    _aide, etape = A_VENIR[args.commande]
    print(f"« moteur {args.commande} » n'est pas encore disponible : il arrive à l'étape {etape}.",
          file=sys.stderr)
    return PAS_ENCORE


if __name__ == "__main__":
    sys.exit(principal())
