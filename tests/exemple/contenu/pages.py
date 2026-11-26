"""Pages propres du parcours d'exemple : l'accueil et une page d'outils."""
import html


def pages(site):
    items = "".join('<li>%s</li>' % site.lien(e.id) for e in site.parcours.etapes())
    accueil = '%s<main class="accueil"><h1>%s</h1><ul>%s</ul></main>%s' % (
        site.barre("index.html"), html.escape(site.reglages.titre_long), items, site.pied())
    outils = "%s<main><h1>Outils</h1></main>%s" % (site.barre("outils.html"), site.pied())
    return {
        "index.html": site.coquille(site.reglages.titre_long, accueil),
        "outils.html": site.coquille("Outils — " + site.reglages.titre_long, outils, scripts=("exemple.js",)),
    }
