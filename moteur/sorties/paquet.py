"""Sortie « paquet » : l'archive que la plateforme importe, exactement au format 1 (étape M3).

    manifeste.json          le parcours, ses parties et ses étapes publiées
    etapes/<clé>.html       un fragment HTML statique par étape publiée (moteur.sorties.fragment)

Le format appartient à la plateforme (FORMAT_PAQUET.md). Trois garanties :

1. **Mêmes contrôles que le site** : registre, statuts, cles.lock, vidéos, liens (moteur.verifier).
   On ne peut pas produire un paquet d'un contenu dont le site serait refusé.
2. **Contrôle de la plateforme** : l'archive construite passe dans `lire_paquet`, copie exacte de la
   plateforme (moteur/controle.py). Si elle la refuserait, la construction échoue et rien n'est écrit.
3. **Reproductible** : même contenu → mêmes octets → même empreinte SHA-256, sur toute machine.
   Les entrées du ZIP sont « stockées » (sans compression : deux versions de zlib peuvent compresser
   différemment), datées du 1ᵉʳ janvier 1980, dans un ordre fixe, avec le même « système d'origine »
   et les mêmes droits sous Windows et sous Linux. La plateforme refuse un paquet identique au dernier
   importé : un contenu inchangé ne crée donc pas de version vide.

Seules les étapes publiées sortent ; une partie sans étape publiée est laissée de côté.
"""
import io
import json
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass

from .. import verifier as V
from ..chargement import ErreurConstruction, charger
from ..controle import FORMAT_ACTUEL, PaquetInvalide, lire_paquet
from .fragment import RenduFragment
from .site import Site, rendre_pages

DOSSIER_PAQUET = "_paquet"
DATE_FIXE = (1980, 1, 1, 0, 0, 0)   # la plus ancienne date qu'accepte le format ZIP
SYSTEME_UNIX = 3                    # « système d'origine » des entrées, le même sur toute machine
DROITS = 0o100644 << 16             # fichier ordinaire, rw-r--r--


@dataclass
class Paquet:
    donnees: bytes        # l'archive
    empreinte: str        # SHA-256, calculée par lire_paquet (celle que garde la plateforme)
    manifeste: dict
    laissees: int         # étapes non publiées, laissées de côté


def cle_partie(nom_partie, num):
    """« Module », 3 → « module-3 » : minuscules sans accents, chiffres et tirets (format plateforme)."""
    ascii_ = unicodedata.normalize("NFKD", nom_partie).encode("ascii", "ignore").decode().lower()
    mot = re.sub(r"[^a-z0-9]+", "-", ascii_).strip("-") or "partie"
    return "%s-%s" % (mot, num)


def ecrire_zip(fichiers):
    """L'archive de {nom : octets}, reproductible : manifeste.json d'abord, puis les autres triés."""
    noms = sorted(fichiers, key=lambda n: (n != "manifeste.json", n))
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_STORED) as z:
        for nom in noms:
            info = zipfile.ZipInfo(nom, date_time=DATE_FIXE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = SYSTEME_UNIX
            info.external_attr = DROITS
            z.writestr(info, fichiers[nom])
    return tampon.getvalue()


def manquants(reglages):
    """Les réglages que le paquet exige et que parcours.toml ne donne pas."""
    return ["[parcours] %s manque dans parcours.toml (%s)" % (cle, aide) for cle, aide in (
        ("slug", "identité du parcours sur la plateforme, ex. slug = \"complexite-algorithmes\""),
        ("matiere", "ex. matiere = \"Informatique\""),
        ("cycle", "lycee, prepa ou universite"),
    ) if not getattr(reglages, cle)]


def fabriquer(depot):
    """Construit le paquet en mémoire. Renvoie (Paquet, résultat des contrôles) ; lève ErreurConstruction.

    Rien n'est écrit."""
    site = Site(depot)
    resultat = V.controler(site, rendre_pages(site))
    erreur = resultat.erreur()
    if erreur:
        raise erreur
    g = depot.reglages
    pbs = manquants(g)
    if pbs:
        raise ErreurConstruction("Réglages du paquet", pbs)

    rendu = RenduFragment(g.noms_temps, site.dossier_videos, g.url, g.macros)
    fichiers, parties = {}, []
    for p in depot.parcours.parties:
        etapes = []
        for e in p.etapes:
            if not e.publiee:
                continue
            fichier = "etapes/%s.html" % e.id
            fichiers[fichier] = rendu.etape(e).encode("utf-8")
            etapes.append({"cle": e.id, "titre": e.titre, "fichier": fichier, "acces": e.acces,
                           "duree_min": e.minutes})
        if etapes:
            parties.append({"cle": cle_partie(g.nom_partie, p.num),
                            "titre": "%s %s · %s" % (g.nom_partie, p.num, p.titre), "etapes": etapes})
    if rendu.problemes:
        raise ErreurConstruction("Paquet", rendu.problemes)
    if not parties:
        raise ErreurConstruction("Paquet", ["aucune étape publiée : le paquet serait vide (la plateforme exige au "
                                            "moins une partie et une étape)"])

    infos = {"slug": g.slug, "titre": g.titre_long, "matiere": g.matiere, "cycle": g.cycle}
    if g.description:
        infos["description"] = g.description
    manifeste = {"format": FORMAT_ACTUEL, "parcours": infos, "parties": parties}
    fichiers["manifeste.json"] = (json.dumps(manifeste, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    donnees = ecrire_zip(fichiers)

    # Le contrôle de la plateforme, tel quel : s'il refuse, on n'écrit rien.
    try:
        lu = lire_paquet(donnees)
    except PaquetInvalide as err:
        raise ErreurConstruction("Paquet refusé par le contrôle de la plateforme (moteur/controle.py)",
                                 err.problemes) from None
    laissees = sum(1 for e in depot.parcours.etapes() if not e.publiee)
    return Paquet(donnees, lu.empreinte, manifeste, laissees), resultat


def construire(racine=".", sortie=None):
    """Construit et écrit le paquet. Renvoie (Paquet, chemin du fichier, résultat des contrôles)."""
    depot = charger(racine)
    paquet, resultat = fabriquer(depot)
    chemin = os.path.abspath(sortie or os.path.join(depot.racine, DOSSIER_PAQUET, depot.reglages.slug + ".zip"))
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as f:
        f.write(paquet.donnees)
    return paquet, chemin, resultat


def resume(paquet, chemin):
    m = paquet.manifeste
    nb = sum(len(p["etapes"]) for p in m["parties"])
    lignes = ["Paquet %s (format %d) : %d partie(s), %d étape(s) publiée(s)%s"
              % (m["parcours"]["slug"], m["format"], len(m["parties"]), nb,
                 ", %d non publiée(s) laissée(s) de côté" % paquet.laissees if paquet.laissees else "")]
    for p in m["parties"]:
        lignes.append("  %s : %s" % (p["titre"], ", ".join("%s (%s)" % (e["cle"], e["acces"]) for e in p["etapes"])))
    lignes.append("Contrôle de la plateforme (lire_paquet) : accepté")
    lignes.append("%s — %s octets" % (chemin, format(len(paquet.donnees), ",").replace(",", " ")))
    lignes.append("Empreinte SHA-256 : %s" % paquet.empreinte)
    return "\n".join(lignes)
