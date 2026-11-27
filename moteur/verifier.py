"""Les contrôles d'un parcours, partagés par « moteur verifier » et « moteur construire ».

« moteur verifier » les lance sans rien écrire et affiche tout ce qu'il trouve ;
« moteur construire » lance les mêmes et refuse de construire s'il y a une erreur.
Une même fonction pour les deux : l'action GitHub ne peut pas publier un site que verifier refuserait.

Déjà contrôlé au chargement (moteur.chargement), avant d'arriver ici :
    registre cohérent (identifiants uniques, prérequis connus et placés avant), statuts connus,
    étape vérifiée ou publiée avec son cours.

Contrôlé ici, sur les pages rendues en mémoire :
    erreurs          cles.lock (moteur.cles), vidéos des étapes publiées, liens internes du cours publié
    avertissements   prérequis non publié d'une étape publiée, vidéo manquante dans un cours non publié

Une erreur bloque la construction ; un avertissement est à regarder, mais ne bloque pas.
"""
import html
import os
import re
from dataclasses import dataclass, field

from . import blocs as B
from . import cles as C
from .chargement import ErreurConstruction

_HREF = re.compile(r'\shref="([^"]*)"')
_ID = re.compile(r'\sid="([^"]+)"')
_EXTERNE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")   # https:, mailto:, //cdn… : pas vérifiés


@dataclass
class Resultat:
    """erreurs : liste de (titre, problèmes), dans l'ordre des contrôles ; avertissements : liste de phrases."""
    erreurs: list = field(default_factory=list)
    avertissements: list = field(default_factory=list)

    def ajouter(self, titre, problemes):
        if problemes:
            self.erreurs.append((titre, list(problemes)))

    @property
    def nb_erreurs(self):
        return sum(max(1, len(pbs)) for _titre, pbs in self.erreurs)

    def erreur(self):
        """La première erreur, prête à être levée par la construction ; None s'il n'y en a pas."""
        if not self.erreurs:
            return None
        titre, pbs = self.erreurs[0]
        return ErreurConstruction(titre, pbs)

    def rapport(self):
        lignes = []
        if self.erreurs:
            lignes.append("Erreurs (la construction sera refusée) :")
            for titre, pbs in self.erreurs:
                lignes.append("  " + str(ErreurConstruction(titre, pbs)).replace("\n", "\n  "))
        if self.avertissements:
            lignes.append("Avertissements (à regarder, ne bloquent pas) :")
            lignes += ["  - " + a for a in self.avertissements]
        if self.erreurs:
            lignes.append("%d erreur(s), %d avertissement(s)." % (self.nb_erreurs, len(self.avertissements)))
        else:
            lignes.append("Aucune erreur, %d avertissement(s)." % len(self.avertissements))
        return "\n".join(lignes)


def videos_citees(corps):
    """Les fichiers vidéo cités par un cours : blocs video(…) et balises src="videos/…" écrites à la main."""
    cites = []
    for n in B.parcourir(corps):
        if isinstance(n, B.Video):
            cites.append(n.fichier)
        elif isinstance(n, str):
            cites += re.findall(r'src="videos/([^"]+)"', n)
    return cites


def videos_manquantes(site, etapes):
    return [(e, v) for e in etapes for v in videos_citees(e.corps)
            if not os.path.exists(os.path.join(site.dossier_videos, v))]


def liens_casses(site, pages):
    """Les liens internes du cours publié qui mènent nulle part.

    Un lien « page.html#ancre » doit viser une page du site et une ancre (id="…") de cette page ;
    « #ancre » vise la page de la partie de l'étape. Les liens externes (https:…) et les liens vers
    d'autres fichiers (vidéos, images) ne sont pas vérifiés ici.
    """
    ancres = {nom: set(_ID.findall(contenu)) for nom, contenu in pages.items()}
    pbs = []
    for e in site.parcours.etapes():
        if not e.publiee:
            continue
        page_etape = site.parcours.partie_de(e.id).fichier
        for lien in _HREF.findall(site.rendre(e.corps)):
            lien = html.unescape(lien)
            if _EXTERNE.match(lien):
                continue
            chemin, _diese, ancre = lien.partition("#")
            if chemin and not chemin.endswith(".html"):
                continue
            cible = chemin or page_etape
            if cible not in pages:
                pbs.append("%s : lien vers %s, mais la page %s n'existe pas" % (e.id, lien, cible))
            elif ancre and ancre not in ancres[cible]:
                pbs.append("%s : lien vers %s, mais %s n'a pas d'ancre #%s" % (e.id, lien, cible, ancre))
    return pbs


def controler(site, pages):
    """Tous les contrôles sur un parcours chargé et ses pages rendues ({nom : HTML}). Renvoie un Resultat."""
    r = Resultat()
    parcours = site.parcours

    try:
        r.ajouter("Clés publiées (cles.lock)", C.controler(parcours, C.lire(site.depot.racine)))
    except C.ErreurCles as err:
        r.erreurs.append((str(err), []))

    publiees = [e for e in parcours.etapes() if e.publiee]
    r.ajouter("Vidéos", ["%s : vidéo manquante videos/%s" % (e.id, v) for e, v in videos_manquantes(site, publiees)])
    r.ajouter("Liens", liens_casses(site, pages))

    for e in publiees:
        for p in e.prereq:
            if not parcours.etape(p).publiee:
                r.avertissements.append("%s (publiée) : son prérequis %s n'est pas publié, le lien mène à sa fiche"
                                        % (e.id, p))
    non_publiees = [e for e in parcours.etapes() if not e.publiee and e.redigee]
    for e, v in videos_manquantes(site, non_publiees):
        r.avertissements.append("%s (%s) : vidéo manquante videos/%s, à ajouter avant de publier"
                                % (e.id, e.statut, v))
    return r
