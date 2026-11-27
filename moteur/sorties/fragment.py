"""Rendu « fragment » : le cours d'une étape en HTML statique, pour le paquet de la plateforme (M3).

La plateforme refuse tout fragment qui pourrait exécuter du code (voir moteur/controle.py) :
pas de <script>, <style>, <form>, <input>, <button>, <textarea>… Le rendu du site en met partout
(onglets des quatre temps, bouton « copier », QCM, ateliers). Ce rendu-ci en est la version statique :

- les blocs déjà statiques (retenir, preuve, exercice, tableau…) reprennent le rendu du site ;
- les quatre temps deviennent des sections à la suite, sans onglets ;
- les composants interactifs (QCM, atelier, Sage, animateur, mesure) sortent sous une forme lisible :
  énoncé, code, corrigé dans un <details>. Ils gardent un attribut data-composant : à M4, la
  plateforme saura les monter à cet endroit ;
- les vidéos et les liens relatifs pointent vers le site public ([site] url de parcours.toml),
  puisque le format 1 n'admet aucun fichier annexe ;
- les macros TeX du parcours sont développées : la plateforme rend les formules avec KaTeX,
  qui ne connaît pas les macros de parcours.toml.

Les problèmes trouvés (vidéo ou lien relatif sans [site] url) sont rassemblés dans `problemes`.
"""
import html
import os
import re

from .. import blocs as B
from .site import RENDUS as RENDUS_SITE, _MATHS, Rendu, proteger_maths

NOTE_INTERACTIF = ('<p class="statique">Version statique : la version interactive arrive bientôt sur '
                   'la plateforme.</p>')

_HREF = re.compile(r'(\shref=")([^"]*)(")')
_EXTERNE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")


class RenduFragment(Rendu):
    """Comme Rendu (site), mais sans aucun script ni contrôle de formulaire.

    url     adresse publique du site, terminée par « / » ; vide si le parcours n'en a pas
    macros  macros TeX du parcours (nom → définition), développées dans les formules
    """

    def __init__(self, temps, videos, url="", macros=None):
        super().__init__(temps, videos)
        self.url = url
        self.macros = dict(macros or {})
        self.problemes = []
        self.ou = "?"  # étape en cours de rendu, pour situer les problèmes

    def __call__(self, noeud):
        if isinstance(noeud, str):
            return noeud
        fonction = RENDUS.get(type(noeud))
        if fonction is None:
            raise TypeError("pas de rendu fragment pour %s" % type(noeud).__name__)
        return fonction(self, noeud)

    def noter(self, probleme):
        self.problemes.append("%s : %s" % (self.ou, probleme))

    # — la page d'une étape —
    def etape(self, e):
        """Le fragment complet d'une étape publiée : objectif, puis le cours."""
        self.ou = e.id
        corps = '<p class="objectif">%s</p>%s' % (html.escape(e.objectif), self(e.corps))
        return self.finir(corps)

    def finir(self, texte):
        """Après le rendu : formules protégées, macros développées, liens relatifs vers le site public."""
        texte = proteger_maths(texte)
        if self.macros:
            texte = _MATHS.sub(lambda m: developper_macros(m.group(0), self.macros), texte)
        return _HREF.sub(self._lien, texte)

    def _lien(self, m):
        cible = m.group(2)
        if not cible or cible.startswith("#") or _EXTERNE.match(cible):
            return m.group(0)
        if not self.url:
            self.noter("lien relatif « %s » : indique l'adresse du site public dans parcours.toml "
                       "([site] url) pour qu'il pointe vers le site" % cible)
            return m.group(0)
        return m.group(1) + html.escape(self.url, quote=True) + cible + m.group(3)


def developper_macros(formule, macros):
    """Remplace \\nom par sa définition, tant qu'il en reste (une macro peut en utiliser une autre)."""
    motif = re.compile(r"\\(%s)(?![A-Za-z])" % "|".join(
        re.escape(n) for n in sorted(macros, key=len, reverse=True)))
    for _ in range(10):  # garde-fou contre une macro qui s'appellerait elle-même
        nouvelle = motif.sub(lambda m: macros[m.group(1)], formule)
        if nouvelle == formule:
            break
        formule = nouvelle
    return formule


# ─────────────────────────────────────────────────────────────────────────────
# Les blocs qui changent par rapport au site
# ─────────────────────────────────────────────────────────────────────────────

def _code(r, b):
    cls = " sage" if b.lang.lower().startswith("sage") else ""
    out = '<pre class="sortie">%s</pre>' % html.escape(b.sortie.strip("\n")) if b.sortie else ""
    return ('<div class="code"><div class="code-h"><p class="lab">%s</p><span class="code-lang%s">%s</span></div>'
            '<pre>%s</pre>%s</div>' % (r(b.titre), cls, html.escape(b.lang), html.escape(b.src.strip("\n")), out))


def _code_de_depart(r, src, lang="python", titre="Code de départ"):
    return r(B.Code(src=src, lang=lang, sortie=None, titre=titre)) if src.strip() else ""


def _qcm(r, b):
    titre = {"entree": "Test d'entrée — as-tu besoin de cette étape ?",
             "sortie": "Test de sortie — valide l'étape"}[b.role]
    questions = []
    for q in b.questions:
        choix = "".join("<li>%s</li>" % r(o) for o in q.options)
        lettre = "abcdefghijklmnopqrstuvwxyz"[q.bonne]
        explication = r(q.explication) if q.explication else ""
        questions.append(
            '<li class="qcm-q"><p>%s</p><ol class="qcm-choix" type="a">%s</ol>'
            '<details><summary>Voir la réponse</summary><p><b>Réponse %s)</b> %s</p>%s</details></li>'
            % (r(q.enonce), choix, lettre, r(q.options[q.bonne]), explication))
    return ('<div class="qcm" data-composant="qcm" data-role="%s"><p class="lab">%s</p>'
            '<p>Réponds sur ta feuille, puis ouvre chaque réponse.</p><ol class="qcm-questions">%s</ol>%s</div>'
            % (b.role, titre, "".join(questions), NOTE_INTERACTIF))


def _quatre_temps(r, b):
    contenus = [r(b.comprendre), r(b.demontrer), r(b.implementer),
                r(b.exercer) + r(b.sortie) + r(b.retenir)]
    sections = "".join('<section class="temps" data-t="%d"><h3>%d. %s</h3>%s</section>'
                       % (i, i + 1, html.escape(nom), contenu)
                       for i, (nom, contenu) in enumerate(zip(r.temps, contenus)))
    return r(b.entree) + sections


def _atelier(r, b):
    corrige = ('<details><summary>Voir le corrigé (après avoir essayé)</summary>%s</details>' % r(b.corrige)
               if b.corrige else "")
    return ('<div class="atelier" data-composant="atelier" data-id="%s"><p class="lab">Atelier — à toi de coder</p>'
            '%s%s%s%s</div>'
            % (html.escape(b.ident, quote=True), r(b.consigne), _code_de_depart(r, b.depart), NOTE_INTERACTIF, corrige))


def _sage_atelier(r, b):
    return ('<div class="sage-atelier" data-composant="sage"><p class="lab">Vérifie avec SageMath</p>%s%s%s</div>'
            % (r(b.consigne), _code_de_depart(r, b.depart, "sage", "Cellule SageMath"), NOTE_INTERACTIF))


def _entree(e):
    """Une entrée d'exemple de l'animateur : [« légende », valeurs] ou des valeurs seules."""
    if isinstance(e, (list, tuple)) and len(e) == 2 and isinstance(e[0], str):
        legende, valeurs = e
        if _valeurs(valeurs) in html.escape(legende):   # « L'exemple : 3, 8, 2, 6 » dit déjà les valeurs
            return html.escape(legende)
        return "%s : %s" % (html.escape(legende), _valeurs(valeurs))
    return _valeurs(e)


def _valeurs(v):
    if isinstance(v, (list, tuple)):
        return html.escape(", ".join(str(x) for x in v))
    return html.escape(str(v))


def _animateur(r, b):
    entrees = "".join("<li>%s</li>" % _entree(e) for e in b.entrees)
    exemples = '<p>Fais tourner l\'algorithme à la main sur ces entrées :</p><ul>%s</ul>' % entrees if entrees else ""
    return ('<div class="anim" data-composant="animateur" data-id="%s" data-algo="%s"><p class="lab">Animateur — %s</p>'
            '%s%s</div>' % (html.escape(b.ident, quote=True), html.escape(b.algo, quote=True), r(b.legende),
                            exemples, NOTE_INTERACTIF))


def _mesure(r, b):
    return ('<div class="mesure" data-composant="mesure" data-atelier="%s"><p class="lab">Mesure — ce que ton code '
            'fait vraiment</p>%s%s</div>' % (html.escape(b.ident, quote=True), r(b.consigne), NOTE_INTERACTIF))


def _video(r, b):
    if not r.url:
        r.noter("vidéo %s : indique l'adresse du site public dans parcours.toml ([site] url), "
                "d'où la plateforme lira la vidéo" % b.fichier)
        return ""
    base = b.fichier.rsplit(".", 1)[0]
    adresse = html.escape(r.url, quote=True) + "videos/"
    piste = ""
    if os.path.exists(os.path.join(r.videos, base + ".vtt")):
        piste = ('<track kind="subtitles" srclang="fr" label="Français" src="%s%s.vtt" default>'
                 % (adresse, html.escape(base, quote=True)))
    return ('<figure class="video"><video controls preload="metadata" playsinline crossorigin="anonymous" '
            'src="%s%s">%s</video><figcaption><span class="tag">Vidéo</span> %s <span class="dur">%s</span>'
            '</figcaption></figure>' % (adresse, html.escape(b.fichier, quote=True), piste, r(b.legende),
                                        html.escape(b.duree)))


RENDUS = dict(RENDUS_SITE)
RENDUS.update({
    B.Code: _code,
    B.Qcm: _qcm,
    B.QuatreTemps: _quatre_temps,
    B.Atelier: _atelier,
    B.SageAtelier: _sage_atelier,
    B.Animateur: _animateur,
    B.Mesure: _mesure,
    B.Video: _video,
})
