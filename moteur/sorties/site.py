"""Sortie « site statique » : les pages HTML, le style et les outils, dans le dossier de sortie.

Repris de build.py et briques.py de Complexité, à l'octet près : la preuve de M1 est que le site
de Complexité est identique avant et après (moteur comparer). Chaque classe de bloc a ici sa
fonction de rendu ; les autres sorties (paquet, LaTeX) auront les leurs.
"""
import html
import json
import os
import re
import shutil
from importlib import resources

from .. import blocs as B
from ..chargement import ErreurConstruction, charger
from ..registre import BROUILLON, PUBLIE, STATUTS, VERIFIE

THEME_BTN = '<button type="button" class="theme-btn" aria-pressed="false">Thème sombre</button>'

# Fichiers JavaScript du moteur, copiés dans assets/ avec les réglages du parcours injectés.
# Aperçu des brouillons (moteur construire --brouillons) : dossier par défaut, bandeau et pastille.
DOSSIER_APERCU = "_apercu"
BANDEAUX = {BROUILLON: "brouillon, non publié", VERIFIE: "vérifié, pas encore publié"}
PASTILLES = {BROUILLON: "brouillon", VERIFIE: "vérifiée"}

JS_MOTEUR = ("site.js", "atelier.js", "atelier-worker.js", "mesure.js", "outils.js")


def modele():
    """Le dossier modele/ installé avec le moteur (style, JS, MathJax, polices, Pyodide)."""
    return resources.files("moteur") / "modele"


# ─────────────────────────────────────────────────────────────────────────────
# Rendu des blocs
# ─────────────────────────────────────────────────────────────────────────────

_MATHS = re.compile(r"(\\\((?:.|\n)+?\\\)|\\\[(?:.|\n)+?\\\])")


def proteger_maths(texte):
    """Dans les formules, < et > deviennent \\lt et \\gt : sinon le navigateur y voit des balises."""
    return _MATHS.sub(lambda m: m.group(0).replace("<", r"\lt ").replace(">", r"\gt "), texte)


class Rendu:
    """Transforme un bloc (ou du HTML simple) en HTML du site.

    temps   noms des quatre temps du gabarit
    videos  dossier des vidéos du parcours (pour joindre les sous-titres .vtt)
    """

    def __init__(self, temps, videos):
        self.temps = list(temps)
        self.videos = videos

    def __call__(self, noeud):
        if isinstance(noeud, str):
            return noeud
        fonction = RENDUS.get(type(noeud))
        if fonction is None:
            raise TypeError("pas de rendu site pour %s" % type(noeud).__name__)
        return fonction(self, noeud)


def _suite(r, b):
    return "".join(r(m) for m in b.morceaux)


def _retenir(r, b):
    return '<div class="retenir"><p class="lab">%s</p>%s</div>' % (r(b.label), r(b.corps))


def _demo(r, b):
    return '<div class="demo"><p class="lab">%s</p>%s<p class="cqfd">∎</p></div>' % (r(b.label), r(b.corps))


def _encadre(classe):
    def rendu(r, b):
        return '<div class="%s"><p class="lab">%s</p>%s</div>' % (classe, r(b.label), r(b.corps))
    return rendu


def _code(r, b):
    cls = "sage" if b.lang.lower().startswith("sage") else ""
    out = ""
    if b.sortie:
        out = '<pre class="sortie">%s</pre>' % html.escape(b.sortie.strip("\n"))
    return ('<div class="code tex2jax_ignore"><div class="code-h">'
            '<p class="lab">%s</p><span class="code-lang %s">%s</span>'
            '<button type="button" class="copier">copier</button></div>'
            '<pre>%s</pre>%s</div>'
            % (r(b.titre), cls, b.lang, html.escape(b.src.strip("\n")), out))


def _remarque(r, remarque):
    return r(B.prof(remarque, "Remarque")) if remarque else ""


def _exo(r, b):
    niv = '<span class="niv">%s</span>' % r(b.niveau) if b.niveau else ""
    return ('<article class="exo"><p class="exo-n">Exercice %s%s</p>'
            '<div class="exo-q">%s</div>'
            '<details class="tex2jax_ignore"><summary>Voir la correction</summary>'
            '<div class="copie"><p class="lab">Correction</p>%s</div>%s</details></article>'
            % (b.n, niv, r(b.enonce), r(b.correction), _remarque(r, b.remarque)))


def _video(r, b):
    base = b.fichier.rsplit(".", 1)[0]
    piste = ""
    if os.path.exists(os.path.join(r.videos, base + ".vtt")):
        piste = '<track kind="subtitles" srclang="fr" label="Français" src="videos/%s.vtt" default>' % base
    return ('<figure class="video"><video controls preload="metadata" playsinline src="videos/%s">%s'
            '</video><figcaption><span class="tag">Vidéo</span> %s '
            '<span class="dur">%s</span></figcaption></figure>' % (b.fichier, piste, r(b.legende), b.duree))


def _video_attente(r, b):
    return ('<figure class="video attente"><div class="ph"><p>Vidéo à venir : %s</p></div>'
            '<figcaption><span class="tag soon">Vidéo</span> en préparation</figcaption></figure>'
            % r(b.sujet))


def _qcm(r, b):
    titre = {"entree": "Test d'entrée — as-tu besoin de cette étape ?",
             "sortie": "Test de sortie — valide l'étape"}[b.role]
    questions = []
    for i, q in enumerate(b.questions):
        choix = "".join(
            '<label class="qcm-o"><input type="radio" name="q%d" value="%d"> <span>%s</span></label>'
            % (i, k, r(o)) for k, o in enumerate(q.options))
        questions.append('<fieldset class="qcm-q" data-bonne="%d"><legend>%d. %s</legend>%s'
                         '<p class="qcm-x" hidden>%s</p></fieldset>'
                         % (q.bonne, i + 1, r(q.enonce), choix, r(q.explication)))
    return ('<form class="qcm" data-role="%s" data-seuil="%d"><p class="lab">%s</p>%s'
            '<div class="qcm-bas"><button type="submit" class="btn">Corriger</button>'
            '<p class="qcm-res" role="status" hidden></p></div></form>'
            % (b.role, b.seuil, titre, "".join(questions)))


def _preuve(r, b):
    plan = "".join("<li>%s</li>" % r(e) for e in b.etapes)
    return ('<div class="preuve">%s'
            '<div class="idee"><p class="lab">L\'idée en une phrase</p><p>%s</p></div>'
            '<div class="squelette"><p class="lab">Le squelette — complète chaque étape sur ta feuille</p>'
            '<ol>%s</ol></div>'
            '<details class="tex2jax_ignore"><summary>Voir la démonstration complète</summary>%s</details>'
            '</div>' % (r(B.retenir(b.enonce_label, b.enonce)), r(b.idee), plan, r(B.demo(b.complete))))


def _exercice(r, b):
    return ('<article class="exo"><p class="exo-n">Exercice %s<span class="niv">%s</span></p>'
            '<div class="exo-q">%s</div>'
            '<details class="indice tex2jax_ignore"><summary>Un indice</summary><div class="prof">%s</div></details>'
            '<details class="tex2jax_ignore"><summary>Voir la correction</summary>'
            '<div class="copie"><p class="lab">Correction</p>%s</div>%s</details></article>'
            % (b.n, r(b.niveau), r(b.enonce), r(b.indice), r(b.correction), _remarque(r, b.remarque)))


def _a_toi(r, b):
    return ('<div class="atoi"><p class="lab">À toi</p>%s'
            '<details class="tex2jax_ignore"><summary>Voir une solution</summary>%s</details></div>'
            % (r(b.enonce), r(b.solution)))


def _a_retenir(r, b):
    return r(B.retenir("À retenir", "<ul>%s</ul>" % "".join("<li>%s</li>" % r(l) for l in b.lignes)))


def _quatre_temps(r, b):
    noms = r.temps
    contenus = [r(b.comprendre), r(b.demontrer), r(b.implementer),
                r(b.exercer) + r(b.sortie) + r(b.retenir)]
    onglets = "".join(
        '<button type="button" role="tab" class="onglet" aria-selected="%s" data-t="%d">'
        '<span class="o-n">%d</span>%s</button>' % ("true" if i == 0 else "false", i, i + 1, nom)
        for i, nom in enumerate(noms))
    panneaux = "".join(
        '<div class="panneau" role="tabpanel" data-t="%d"%s>%s'
        '<p class="suite">%s</p></div>'
        % (i, "" if i == 0 else " hidden", contenu,
           '<button type="button" class="btn ghost aller" data-t="%d">Temps suivant : %s →</button>'
           % (i + 1, noms[i + 1]) if i + 1 < len(noms) else "")
        for i, contenu in enumerate(contenus))
    return ('%s<div class="temps"><div class="onglets" role="tablist">%s</div>%s</div>'
            % (r(b.entree), onglets, panneaux))


def _atelier(r, b):
    return ('<div class="atelier" data-id="%s"><p class="lab">Atelier — à toi de coder</p>%s'
            '<textarea class="at-code" spellcheck="false" autocapitalize="off" autocomplete="off" '
            'autocorrect="off" rows="%d" aria-label="Ton code Python">%s</textarea>'
            '<script type="application/json" class="atelier-tests">%s</script>'
            '<div class="atelier-b"><button type="button" class="btn ghost at-executer">Exécuter</button>'
            '<button type="button" class="btn at-tester">Tester mon code</button>'
            '<button type="button" class="at-reinit">Réinitialiser</button>'
            '<span class="atelier-etat" role="status"></span></div>'
            '<div class="atelier-res" hidden></div>'
            '<details class="atelier-corrige tex2jax_ignore" hidden><summary>Voir le corrigé (après avoir essayé)</summary>%s</details>'
            '</div>'
            % (b.ident, r(b.consigne), b.depart.strip("\n").count("\n") + 3, html.escape(b.depart.strip("\n")),
               json.dumps(list(b.tests), ensure_ascii=False).replace("</", "<\\/"), r(b.corrige)))


def _sage_atelier(r, b):
    return ('<div class="sage-atelier"><p class="lab">Vérifie avec SageMath</p>%s'
            '<div class="sage-cellule tex2jax_ignore" hidden><script type="text/x-sage">%s</script></div>'
            '<div class="atelier-b"><button type="button" class="btn ghost sage-ouvrir">Ouvrir la cellule SageMath</button>'
            '<span class="sage-msg" role="status"></span></div></div>'
            % (r(b.consigne), html.escape(b.depart.strip("\n"))))


def _methode(r, b):
    return ('<div class="methode"><p class="lab">Méthode — %s</p><ol>%s</ol></div>'
            % (r(b.titre), "".join("<li>%s</li>" % r(e) for e in b.etapes)))


def _animateur(r, b):
    return ('<div class="anim" data-id="%s" data-algo="%s" data-entrees="%s">'
            '<p class="lab">Animateur — %s</p><noscript>L&#39;animateur a besoin de JavaScript.</noscript></div>'
            % (b.ident, b.algo, html.escape(json.dumps(b.entrees, ensure_ascii=False)), r(b.legende)))


def _mesure(r, b):
    return ('<div class="mesure" data-atelier="%s" data-fonction="%s" data-tailles="%s" data-courbes="%s" '
            'data-cas="%s" data-ratios="%s" data-axe="%s">'
            '<p class="lab">Mesure — ce que ton code fait vraiment</p>%s'
            '<div class="atelier-b"><button type="button" class="btn m-lancer">Mesurer et tracer</button>'
            '<span class="m-etat" role="status"></span></div>'
            '<div class="m-graphe" hidden></div></div>'
            % (b.ident, b.fonction, json.dumps(b.tailles), html.escape(json.dumps(b.courbes, ensure_ascii=False)),
               html.escape(json.dumps(b.cas, ensure_ascii=False)),
               html.escape(json.dumps(list(b.ratios), ensure_ascii=False)),
               html.escape(b.axe), r(b.consigne)))


def _tableau(r, b):
    t = "".join("<th>%s</th>" % r(h) for h in b.entetes)
    corps = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % r(c) for c in l) for l in b.lignes)
    return ('<div class="table-wrap"><table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            % (b.classe, t, corps))


RENDUS = {
    B.Suite: _suite,
    B.Retenir: _retenir,
    B.Demo: _demo,
    B.Prof: _encadre("prof"),
    B.Master: _encadre("master"),
    B.Examen: _encadre("examen"),
    B.Methode: _methode,
    B.ARetenir: _a_retenir,
    B.AToi: _a_toi,
    B.Preuve: _preuve,
    B.Exercice: _exercice,
    B.Exo: _exo,
    B.Qcm: _qcm,
    B.QuatreTemps: _quatre_temps,
    B.Code: _code,
    B.Tableau: _tableau,
    B.Video: _video,
    B.VideoAttente: _video_attente,
    B.Atelier: _atelier,
    B.SageAtelier: _sage_atelier,
    B.Animateur: _animateur,
    B.Mesure: _mesure,
}


# ─────────────────────────────────────────────────────────────────────────────
# Les pages
# ─────────────────────────────────────────────────────────────────────────────

def _js_chaine(texte):
    """Un littéral JavaScript entre apostrophes."""
    return "'%s'" % (texte.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n"))


class Site:
    """Ce dont les pages ont besoin. Les pages propres d'un parcours (contenu/pages.py) le reçoivent
    et utilisent ses fonctions : coquille, barre, pied, lien, rendre."""

    def __init__(self, depot, apercu=False):
        self.depot = depot
        self.apercu = apercu  # vrai pour « moteur construire --brouillons » : jamais publié
        self.reglages = depot.reglages
        self.parcours = depot.parcours
        self.dossier_videos = os.path.join(depot.racine, self.reglages.videos)
        self.rendre = Rendu(self.reglages.noms_temps, self.dossier_videos)

    def montre_cours(self, e):
        """Vrai si le cours de l'étape sort dans cette construction.

        Site normal : les étapes publiées seulement. Aperçu (--brouillons) : tout le cours écrit.
        """
        return e.publiee or (self.apercu and e.redigee)

    # — morceaux communs —
    def mathjax(self):
        macros = ["%s:%s" % (k, _js_chaine(v)) for k, v in self.reglages.macros.items()]
        lignes = [", ".join(macros[i:i + 4]) for i in range(0, len(macros), 4)]
        return """<script>
window.MathJax = {
  tex: {
    inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']],
    macros: { %s }
  },
  options: { skipHtmlTags: ['script','noscript','style','textarea','pre','code'], ignoreHtmlClass: 'tex2jax_ignore' },
  svg: { fontCache: 'global' }
};
</script>
<script defer src="assets/mathjax/tex-svg.js"></script>""" % (",\n              ".join(lignes))

    def theme_init(self):
        return ("<script>try{var t=localStorage.getItem('%s-theme');"
                "if(t)document.documentElement.dataset.theme=t;}catch(e){}</script>"
                % self.reglages.prefixe_stockage)

    def pied(self):
        return ('<footer class="pied"><p>© %d %s · Contenu sous licence '
                '<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.fr">CC BY-NC-SA 4.0</a>, '
                'code sous licence MIT. Site personnel, sans lien officiel avec une université.</p></footer>'
                % (self.reglages.annee, self.reglages.auteur))

    def barre(self, courant=""):
        l = "".join('<a href="%s"%s>%s</a>' % (x.lien, ' aria-current="page"' if x.lien == courant else "", x.texte)
                    for x in self.reglages.barre)
        return ('<header class="barre"><a class="barre-brand" href="index.html">%s</a>'
                '<nav class="barre-liens" aria-label="Pages">%s</nav><span style="flex:1"></span>%s</header>'
                % (self.reglages.titre, l, THEME_BTN))

    def coquille(self, titre, body, data="", scripts=()):
        g = self.reglages
        js = "".join('<script defer src="assets/%s"></script>' % s for s in scripts)
        icone = '\n<link rel="icon" href="%s">' % g.icone if g.icone else ""
        return """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%s</title>
<meta name="description" content="%s">%s
<link rel="stylesheet" href="assets/style.css">
%s
%s
</head>
<body%s>
%s
<script defer src="assets/outils.js"></script>%s
</body>
</html>
""" % (html.escape(titre), html.escape(g.description, quote=False).replace('"', "&quot;"), icone,
       self.theme_init(), self.mathjax(), data, body, js)

    def lien(self, eid):
        e, p = self.parcours.index[eid]
        return '<a href="%s#%s">%s %s</a>' % (p.fichier, eid, self.parcours.numero(eid), html.escape(e.titre))

    # — pages des parties —
    def fiche(self, e):
        pre = ", ".join(self.lien(p) for p in e.prereq) or '<span class="rien">aucun — on peut commencer ici</span>'
        ouv = ", ".join(self.lien(s.id) for s in self.parcours.suites(e.id)) or '<span class="rien">—</span>'
        lignes = '<dt>Prérequis</dt><dd>%s</dd><dt>Sert ensuite à</dt><dd>%s</dd>' % (pre, ouv)
        if e.examen:
            lignes += '<dt>À l\'examen</dt><dd><span class="pastille exam">%s</span></dd>' % html.escape(e.examen)
        if e.cours:
            lignes += '<dt>Dans le cours</dt><dd>%s</dd>' % html.escape(e.cours)
        return '<div class="fiche"><dl>%s</dl></div>' % lignes

    def section_etape(self, e, p):
        if self.montre_cours(e):
            corps = self.rendre(e.corps)
            if not e.publiee:
                # Aperçu seulement : on réutilise le style de l'encadré « à venir » pour ne pas
                # toucher au style commun (le site publié doit rester identique à l'octet).
                corps = ('<div class="a-venir"><p class="lab">Aperçu — %s</p></div>'
                         % BANDEAUX[e.statut]) + corps
        else:
            corps = ('<div class="a-venir"><p class="lab">Étape en cours de rédaction</p>'
                     '<p>Le cours arrive. En attendant, la fiche ci-dessus dit ce qu\'il faudra savoir faire, '
                     'ce qu\'il faut avoir vu avant, et à quoi l\'étape servira ensuite.</p></div>')
        num = self.parcours.numero(e.id)
        return ('<section class="lesson" id="%s" data-part="%s" data-num="%s" data-title="%s" hidden>'
                '<header class="lhead"><p class="eyebrow">%s %d · Étape %s<span class="meta">%d min</span></p>'
                '<h2>%s</h2></header><div class="lbody">'
                '<p class="objectif">%s</p>%s%s</div></section>'
                % (e.id, html.escape(p.titre), num, html.escape(e.titre), self.reglages.nom_partie, p.num, num,
                   e.minutes, html.escape(e.titre), html.escape(e.objectif), self.fiche(e), proteger_maths(corps)))

    def page_partie(self, p, suivant):
        g = self.reglages
        lignes = []
        for e in p.etapes:
            if e.publiee:
                statut = '<span class="pastille">rédigée</span>'
            elif self.montre_cours(e):
                statut = '<span class="pastille">%s</span>' % PASTILLES[e.statut]
            else:
                statut = '<span class="rien">à venir</span>'
            lignes.append('<tr><td><a href="#%s">%s %s</a></td><td>%s</td><td>%s</td></tr>'
                          % (e.id, self.parcours.numero(e.id), html.escape(e.titre), html.escape(e.objectif), statut))
        howto = "".join('<div><p class="num">%d</p><p><strong>%s.</strong> %s</p></div>' % (i + 1, nom, consigne)
                        for i, (nom, consigne) in enumerate(g.temps))
        demonstratif = g.demonstratif[:1].upper() + g.demonstratif[1:]
        depart = ('<section class="lesson" id="depart-%d" data-part="" data-title="%s en bref" hidden>'
                  '<header class="lhead"><p class="eyebrow">%s %d</p><h2>%s</h2></header>'
                  '<div class="lbody"><p class="lead">%s</p>'
                  '<div class="howto">%s</div>'
                  '<h3>Les %d étapes de %s</h3><div class="table-wrap"><table><thead><tr><th>Étape</th>'
                  '<th>Ce qu\'on doit savoir faire</th><th>État</th></tr></thead><tbody>%s</tbody></table></div>'
                  '</div></section>'
                  % (p.num, demonstratif, g.nom_partie, p.num, html.escape(p.titre), html.escape(p.resume), howto,
                     len(p.etapes), g.demonstratif, "".join(lignes)))
        sections = [depart] + [self.section_etape(e, p) for e in p.etapes]
        nav_parties = "".join('<li><a href="%s"%s><span class="n-num">%d</span>%s</a></li>'
                              % (x.fichier, ' class="ici"' if x is p else '', x.num, html.escape(x.titre))
                              for x in self.parcours.parties)
        extras = "".join('\n      <li><a href="%s"><span class="n-num">%s</span>%s</a></li>' % (x.lien, x.symbole, x.texte)
                         for x in g.sommaire)
        body = """<div class="app">
  <div class="topbar">
    <button type="button" class="btn ghost" id="menu-btn" aria-controls="side" aria-expanded="false">Sommaire</button>
    <p class="brand">%s %d</p>
    <p class="mini" id="mini-prog"></p>
  </div>
  <div class="scrim" id="scrim" hidden></div>
  <nav class="side" id="side" aria-label="Sommaire %s">
    <p class="brand"><a href="index.html">%s</a></p>
    <p class="brand-sub">%s</p>
    <ul class="niveaux"><li><a href="index.html"><span class="n-num">·</span>Accueil</a></li>%s%s</ul>
    <div class="prog"><div class="prog-bar"><div class="prog-fill" id="prog-fill"></div></div>
      <p class="prog-txt" id="prog-txt"></p></div>
    <div id="nav"></div>
    %s
  </nav>
  <main class="main" id="main">
%s
    <nav class="pager">
      <a class="btn ghost" id="prev" href="#">← Précédent</a>
      <span class="right"><p class="done-note" id="done-note" hidden>Étape validée ✓</p>
      <a class="btn" id="next" href="#">Suivant →</a></span>
    </nav>
    %s
  </main>
</div>""" % (g.nom_partie, p.num, g.complement, g.titre, html.escape(g.sous_titre), nav_parties, extras,
             THEME_BTN, "\n".join(sections), self.pied())
        data = ' data-module="%d"%s' % (p.num, ' data-suivant="%s"' % suivant if suivant else "")
        return self.coquille("%s %d · %s — %s" % (g.nom_partie, p.num, p.titre, g.titre_long), body, data,
                             tuple(g.scripts_partie))


# ─────────────────────────────────────────────────────────────────────────────
# Construction
# ─────────────────────────────────────────────────────────────────────────────

def verifier_videos(site):
    """Chaque vidéo citée dans le cours d'une étape publiée existe dans le dossier des vidéos.

    Un brouillon peut attendre sa vidéo, même dans l'aperçu : « moteur verifier » le signalera
    comme avertissement (E4), sans bloquer la construction.
    """
    pbs = []
    for e in site.parcours.etapes():
        if not e.publiee:
            continue
        cites = []
        for n in B.parcourir(e.corps):
            if isinstance(n, B.Video):
                cites.append(n.fichier)
            elif isinstance(n, str):
                cites += re.findall(r'src="videos/([^"]+)"', n)
        for v in cites:
            if not os.path.exists(os.path.join(site.dossier_videos, v)):
                pbs.append("%s : vidéo manquante videos/%s" % (e.id, v))
    return pbs


def _injecter(contenu, reglages):
    """Les réglages du parcours dans un JS du moteur : préfixe de stockage, message de l'accueil."""
    contenu = contenu.replace(b"__PREFIXE__", reglages.prefixe_stockage.encode("ascii"))
    return contenu.replace(b"'__ACCUEIL_VIDE__'", _js_chaine(reglages.message_accueil_vide).encode("utf-8"))


def copier_assets(site, sortie):
    g, racine, m = site.reglages, site.depot.racine, modele()
    a = os.path.join(sortie, "assets")
    os.makedirs(a, exist_ok=True)
    with open(os.path.join(a, "style.css"), "w", encoding="utf-8") as f:
        f.write((m / "style.css").read_text(encoding="utf-8") + "\n")
        for nom in g.css:
            with open(os.path.join(racine, nom), encoding="utf-8") as css:
                f.write(css.read() + "\n")
    for nom in JS_MOTEUR:
        with open(os.path.join(a, nom), "wb") as f:
            f.write(_injecter((m / nom).read_bytes(), g))
    for nom in g.js:
        shutil.copy(os.path.join(racine, nom), os.path.join(a, os.path.basename(nom)))
    os.makedirs(os.path.join(a, "mathjax"), exist_ok=True)
    with resources.as_file(m / "vendor") as vendor:
        shutil.copy(os.path.join(vendor, "tex-svg.js"), os.path.join(a, "mathjax", "tex-svg.js"))
        for dossier in ("fonts", "pyodide"):
            cible = os.path.join(a, dossier)
            if os.path.exists(cible):
                shutil.rmtree(cible)
            shutil.copytree(os.path.join(vendor, dossier), cible)


def copier_videos(site, sortie):
    cible = os.path.join(sortie, "videos")
    os.makedirs(cible, exist_ok=True)
    source = site.dossier_videos
    if os.path.isdir(source) and os.path.abspath(source) != os.path.abspath(cible):
        shutil.copytree(source, cible, dirs_exist_ok=True)


def construire(racine=".", sortie=None, brouillons=False):
    """Construit le site du parcours. Renvoie (site, dossier de sortie) ; lève ErreurConstruction.

    brouillons  aperçu : sort aussi le cours des étapes en brouillon ou vérifiées, avec un bandeau,
                dans _apercu/ par défaut. Pour relire chez soi ; ce dossier ne se publie jamais.
    """
    depot = charger(racine)
    site = Site(depot, apercu=brouillons)
    pbs = verifier_videos(site)
    if pbs:
        raise ErreurConstruction("Vidéos", pbs)
    defaut = DOSSIER_APERCU if brouillons else depot.reglages.sortie
    sortie = os.path.abspath(sortie or os.path.join(depot.racine, defaut))
    os.makedirs(sortie, exist_ok=True)
    copier_videos(site, sortie)
    copier_assets(site, sortie)
    open(os.path.join(sortie, ".nojekyll"), "w").close()

    pages = {}
    if depot.pages:
        pages.update(depot.pages(site))
    parties = site.parcours.parties
    for k, p in enumerate(parties):
        if p.fichier in pages:
            raise ErreurConstruction("contenu/pages.py écrit %s, qui est la page d'une partie" % p.fichier)
        suivant = parties[k + 1].fichier if k + 1 < len(parties) else None
        pages[p.fichier] = site.page_partie(p, suivant)
    for nom, contenu in pages.items():
        with open(os.path.join(sortie, nom), "w", encoding="utf-8") as f:
            f.write(contenu)
    return site, sortie


def avancement(site, sortie):
    """Le résumé affiché après la construction : où en est chaque statut, partie par partie."""
    etapes = site.parcours.etapes()
    total = len(etapes)
    nb = {st: sum(1 for e in etapes if e.statut == st) for st in STATUTS}
    brouillons_rediges = sum(1 for e in etapes if e.statut == BROUILLON and e.redigee)
    nb_pages = len([n for n in os.listdir(sortie) if n.endswith(".html")])
    titre = "Aperçu (avec les brouillons, à ne pas publier)" if site.apercu else "Site"
    lignes = ["%s construit dans %s : %d pages, %d étapes" % (titre, sortie, nb_pages, total),
              "  %d publiée(s) (%d %%), %d vérifiée(s), %d brouillon(s) dont %d rédigé(s)"
              % (nb[PUBLIE], round(100 * nb[PUBLIE] / total) if total else 0, nb[VERIFIE], nb[BROUILLON],
                 brouillons_rediges)]
    nom = site.reglages.nom_partie.lower()
    for p in site.parcours.parties:
        lignes.append("  %s %d : %2d/%2d publiée(s)  %s" % (nom, p.num, sum(1 for e in p.etapes if e.publiee),
                                                            len(p.etapes), p.titre))
    return "\n".join(lignes)
