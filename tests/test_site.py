"""Tests de `moteur construire` sur le parcours d'exemple (tests/exemple)."""
import re
import shutil
from pathlib import Path

import pytest

from moteur import cli
from moteur.chargement import ErreurConstruction, charger
from moteur.reglages import ErreurReglages, lire
from moteur.sorties.site import construire, modele

EXEMPLE = Path(__file__).parent / "exemple"


@pytest.fixture
def depot(tmp_path):
    """Une copie du parcours d'exemple, qu'un test peut abîmer sans gêner les autres."""
    d = tmp_path / "parcours"
    shutil.copytree(EXEMPLE, d)
    return d


@pytest.fixture
def construit(depot, tmp_path):
    sortie = tmp_path / "site"
    construire(depot, sortie)
    return sortie


def lire_page(sortie, nom):
    return (sortie / nom).read_text(encoding="utf-8")


# — ce que contient le site —

def test_pages_et_assets(construit):
    noms = {p.relative_to(construit).as_posix() for p in construit.rglob("*")}
    for attendu in ("index.html", "outils.html", "chapitre-1.html", "chapitre-2.html", ".nojekyll",
                    "assets/style.css", "assets/site.js", "assets/atelier.js", "assets/atelier-worker.js",
                    "assets/mesure.js", "assets/outils.js", "assets/exemple.js", "assets/mathjax/tex-svg.js",
                    "assets/pyodide/pyodide.js", "assets/fonts/kalam-latin-400-normal.woff2",
                    "videos/demo.mp4", "videos/demo.vtt"):
        assert attendu in noms, attendu


def test_style_commun_puis_style_du_parcours(construit):
    commun = (modele() / "style.css").read_text(encoding="utf-8")
    assert lire_page(construit, "assets/style.css") == commun + "\n" + ".exemple { color: teal; }\n" + "\n"


def test_reglages_injectes_dans_les_js(construit):
    outils = lire_page(construit, "assets/outils.js")
    assert "'exemple-theme'" in outils and "'exemple-progression-'" in outils
    assert "'Rien de validé pour l\\'instant. Commence par la partie 1.'" in outils
    assert "'exemple-progression-'" in lire_page(construit, "assets/site.js")
    assert "'exemple-atelier-'" in lire_page(construit, "assets/atelier.js")
    for nom in ("outils.js", "site.js", "atelier.js"):
        assert "__PREFIXE__" not in lire_page(construit, "assets/" + nom)
    assert "__ACCUEIL_VIDE__" not in outils


def test_copies_a_l_octet_pres(construit):
    for rel in ("vendor/pyodide/pyodide.asm.wasm", "vendor/tex-svg.js", "mesure.js"):
        source = (modele() / rel).read_bytes()
        cible = construit / "assets" / rel.replace("vendor/tex-svg.js", "mathjax/tex-svg.js").replace("vendor/", "")
        assert cible.read_bytes() == source


def test_page_de_partie(construit):
    p = lire_page(construit, "chapitre-1.html")
    assert "<title>Chapitre 1 · Premiers pas — Parcours Exemple du moteur</title>" in p
    assert ' data-module="1" data-suivant="chapitre-2.html">' in p
    assert 'data-title="Ce chapitre en bref"' in p and "Les 2 étapes de ce chapitre" in p
    assert 'aria-label="Sommaire du chapitre"' in p
    assert '<span class="n-num">∑</span>Outils</a></li></ul>' in p
    assert "<strong>Calculer.</strong> Calcule à la main, puis vérifie." in p
    assert 'Chapitre 1 · Étape 1.2<span class="meta">25 min</span>' in p
    assert '<script defer src="assets/exemple.js"></script>' in p
    assert "Étape en cours de rédaction" in p                 # p1-suite n'est pas rédigée
    assert '<span class="pastille exam">Annale 2025, ex. 1</span>' in p
    assert 'Sert ensuite à</dt><dd><a href="chapitre-2.html#p2-loin">2.1 Plus loin</a>' in p


def test_cours_rendu_et_maths_protegees(construit):
    p = lire_page(construit, "chapitre-1.html")
    assert '<p class="lead">Une introduction partagée.</p>' in p      # aide _commun.py importée
    assert r"Si \(a \lt  b\) alors" in p                              # < dans une formule
    assert '<track kind="subtitles" srclang="fr" label="Français" src="videos/demo.vtt" default>' in p
    assert "Temps suivant : Calculer →" in p


def test_coquille(construit):
    p = lire_page(construit, "index.html")
    assert p.startswith("<!doctype html>\n<html lang=\"fr\">\n")
    assert '<meta name="description" content="Parcours d\'exemple : il sert aux tests du moteur &lt;et&gt; rien d\'autre.">' in p
    assert "\n<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E\">\n" in p
    assert "localStorage.getItem('exemple-theme')" in p
    assert ("macros: { N:'\\\\mathbb{N}', Z:'\\\\mathbb{Z}', R:'\\\\mathbb{R}', F:'\\\\mathbb{F}',\n"
            "              pgcd:'\\\\operatorname{pgcd}', cle:'\\\\text{clé}' }") in p
    assert '<a href="index.html" aria-current="page">Accueil</a><a href="outils.html">Outils</a>' in p
    assert p.endswith('<script defer src="assets/outils.js"></script>\n</body>\n</html>\n')


def test_deux_constructions_identiques(depot, tmp_path):
    from moteur.comparer import comparer
    construire(depot, tmp_path / "a")
    construire(depot, tmp_path / "b")
    assert comparer(tmp_path / "a", tmp_path / "b").identiques()


def test_sortie_par_defaut_selon_les_reglages(depot):
    _site, sortie = construire(depot)
    assert Path(sortie) == depot / "_site"
    assert (depot / "_site" / "index.html").exists()


def test_commande_construire(depot, tmp_path, capsys):
    assert cli.principal(["construire", "--dossier", str(depot), "--sortie", str(tmp_path / "s")]) == cli.OK
    sortie = capsys.readouterr().out
    assert "Site construit dans" in sortie and "4 pages, 3 étapes" in sortie
    assert "1 publiée(s) (33 %), 0 vérifiée(s), 2 brouillon(s) dont 0 rédigé(s)" in sortie
    assert "chapitre 1 :  1/ 2 publiée(s)  Premiers pas" in sortie


# — ce que la construction refuse —

def refus(depot, tmp_path):
    with pytest.raises(ErreurConstruction) as err:
        construire(depot, tmp_path / "site")
    return str(err.value)


def test_refus_sans_parcours_toml(tmp_path, capsys):
    assert cli.principal(["construire", "--dossier", str(tmp_path)]) == cli.ECHEC
    assert "Pas de parcours.toml" in capsys.readouterr().err


def test_refus_video_manquante(depot, tmp_path):
    (depot / "videos" / "demo.mp4").unlink()
    assert "p1-depart : vidéo manquante videos/demo.mp4" in refus(depot, tmp_path)


def test_refus_etape_inconnue(depot, tmp_path):
    (depot / "contenu" / "partie2.py").write_text('CORPS = {"fantome": "<p>x</p>"}\n', encoding="utf-8")
    assert "contenu/partie2.py : étape inconnue fantome" in refus(depot, tmp_path)


def test_refus_etape_redigee_deux_fois(depot, tmp_path):
    (depot / "contenu" / "partie9.py").write_text('CORPS = {"p1-depart": "<p>x</p>"}\n', encoding="utf-8")
    assert "étape p1-depart rédigée deux fois" in refus(depot, tmp_path)


def test_refus_corps_qui_n_est_pas_du_cours(depot, tmp_path):
    (depot / "contenu" / "partie2.py").write_text('CORPS = {"p2-loin": 42}\n', encoding="utf-8")
    assert "doit être un bloc ou du HTML, pas int" in refus(depot, tmp_path)


def test_refus_erreur_dans_le_cours(depot, tmp_path):
    (depot / "contenu" / "partie2.py").write_text("from moteur.blocs import retenir\nCORPS = {'p2-loin': '<p>%s</p>' % retenir('a', 'b')}\n",
                                                  encoding="utf-8")
    message = refus(depot, tmp_path)
    assert message.startswith("Erreur dans contenu/partie2.py : TypeError: Retenir est un bloc, pas une chaîne")


def test_refus_registre_incoherent(depot, tmp_path):
    reg = depot / "contenu" / "registre.py"
    reg.write_text(reg.read_text(encoding="utf-8").replace('["p1-suite"]', '["inconnue"]'), encoding="utf-8")
    assert "p2-loin : prérequis inconnu inconnue" in refus(depot, tmp_path)


def test_refus_page_propre_qui_ecrase_une_partie(depot, tmp_path):
    (depot / "contenu" / "pages.py").write_text("def pages(site):\n    return {'chapitre-1.html': 'x'}\n", encoding="utf-8")
    assert "chapitre-1.html" in refus(depot, tmp_path)


def test_chargement_de_deux_parcours_dans_le_meme_processus(depot, tmp_path):
    autre = tmp_path / "autre"
    shutil.copytree(depot, autre)
    reg = autre / "contenu" / "registre.py"
    reg.write_text(reg.read_text(encoding="utf-8").replace("Premiers pas", "Autres pas"), encoding="utf-8")
    assert charger(depot).parcours.parties[0].titre == "Premiers pas"
    assert charger(autre).parcours.parties[0].titre == "Autres pas"


# — réglages —

MINIMAL = '[parcours]\ntitre = "T"\ntitre_long = "Titre"\n'


def test_reglages_minimaux_et_valeurs_par_defaut():
    g = lire(MINIMAL)
    assert (g.sortie, g.nom_partie, g.fichier_partie) == ("_site", "Module", "module-{num}.html")
    assert g.noms_temps == ["Comprendre", "Démontrer", "Implémenter", "S'exercer"]


@pytest.mark.parametrize("texte,message", [
    ('[parcours]\ntitre = "T"\n', "titre_long est obligatoire"),
    (MINIMAL + "[site]\nsorti = 'x'\n", "clé inconnue « sorti » dans [site]"),
    (MINIMAL + "[style]\n", "table inconnue [style]"),
    (MINIMAL + "[parties]\nfichier = 'partie.html'\n", "doit contenir {num}"),
    (MINIMAL + "[site]\nprefixe_stockage = \"a'b\"\n", "prefixe_stockage"),
    (MINIMAL + "[gabarit]\ntemps = [{ nom = 'A', consigne = 'a' }]\n", "4 temps"),
    (MINIMAL + "[[site.barre]]\nlien = 'index.html'\n", "attendu lien, texte"),
    ("[parcours\n", "parcours.toml"),
])
def test_reglages_refuses(texte, message):
    with pytest.raises(ErreurReglages, match=re.escape(message)):
        lire(texte)


def test_refus_statut_inconnu(depot, tmp_path):
    reg = depot / "contenu" / "registre.py"
    reg.write_text(reg.read_text(encoding="utf-8").replace('["p1-suite"]),', '["p1-suite"], statut="publié"),'),
                   encoding="utf-8")
    assert refus(depot, tmp_path) == ("Erreur dans contenu/registre.py : ErreurStatut: étape p2-loin : "
                                      "statut inconnu 'publié' (attendu : brouillon, verifie, publie)")


def test_refus_publie_sans_cours(depot, tmp_path):
    reg = depot / "contenu" / "registre.py"
    reg.write_text(reg.read_text(encoding="utf-8").replace('["p1-suite"]),', '["p1-suite"], statut="publie"),'),
                   encoding="utf-8")
    assert refus(depot, tmp_path) == "Statuts :\n  - p2-loin : statut publie, mais son cours n'est pas écrit"


# — statuts et aperçu (M2, E2) —

def rediger_p1_suite(depot, statut):
    """p1-suite reçoit un cours, avec le statut donné (brouillon, verifie ou publie)."""
    (depot / "contenu" / "partie9.py").write_text(
        'CORPS = {"p1-suite": "<p>Cours de la suite, pas encore relu.</p>"}\n', encoding="utf-8")
    if statut != "brouillon":
        reg = depot / "contenu" / "registre.py"
        reg.write_text(reg.read_text(encoding="utf-8").replace('cours="Chapitre 1"),', 'cours="Chapitre 1", statut="%s"),' % statut),
                       encoding="utf-8")
    if statut == "publie":
        with open(depot / "cles.lock", "a", encoding="utf-8") as f:
            f.write("p1-suite\n")


def section(page, eid):
    """Le HTML de la section d'une étape dans la page de sa partie."""
    debut = page.index('<section class="lesson" id="%s"' % eid)
    return page[debut:page.index("</section>", debut)]


@pytest.mark.parametrize("statut", ["brouillon", "verifie"])
def test_cours_non_publie_ne_sort_pas(depot, tmp_path, statut):
    rediger_p1_suite(depot, statut)
    construire(depot, tmp_path / "site")
    p = section(lire_page(tmp_path / "site", "chapitre-1.html"), "p1-suite")
    assert "Cours de la suite" not in p
    assert "Étape en cours de rédaction" in p                        # la fiche, comme avant
    assert '<span class="rien">à venir</span>' in lire_page(tmp_path / "site", "chapitre-1.html")


def test_cours_publie_sort(depot, tmp_path):
    rediger_p1_suite(depot, "publie")
    construire(depot, tmp_path / "site")
    page = lire_page(tmp_path / "site", "chapitre-1.html")
    p = section(page, "p1-suite")
    assert "<p>Cours de la suite, pas encore relu.</p>" in p
    assert "Aperçu" not in p and "Étape en cours de rédaction" not in p
    assert page.count('<span class="pastille">rédigée</span>') == 2


@pytest.mark.parametrize("statut, bandeau, pastille", [
    ("brouillon", "Aperçu — brouillon, non publié", "brouillon"),
    ("verifie", "Aperçu — vérifié, pas encore publié", "vérifiée"),
])
def test_apercu_montre_les_brouillons_avec_un_bandeau(depot, statut, bandeau, pastille, capsys):
    rediger_p1_suite(depot, statut)
    assert cli.principal(["construire", "--dossier", str(depot), "--brouillons"]) == cli.OK
    apercu = depot / "_apercu"                                       # dossier par défaut de l'aperçu
    page = lire_page(apercu, "chapitre-1.html")
    p = section(page, "p1-suite")
    assert '<div class="a-venir"><p class="lab">%s</p></div><p>Cours de la suite' % bandeau in p
    assert '<span class="pastille">%s</span>' % pastille in page
    assert "Aperçu — " not in section(page, "p1-depart")              # l'étape publiée n'a pas de bandeau
    assert capsys.readouterr().out.startswith("Aperçu (avec les brouillons, à ne pas publier) construit dans")
    assert not (depot / "_site").exists()                            # le site normal n'est pas touché


def test_sans_brouillon_l_apercu_egale_le_site(depot, tmp_path):
    # Aucun brouillon rédigé : l'aperçu ne doit rien ajouter au site.
    from moteur.comparer import comparer
    construire(depot, tmp_path / "site")
    construire(depot, tmp_path / "apercu", brouillons=True)
    assert comparer(tmp_path / "site", tmp_path / "apercu").identiques()


def test_video_manquante_dans_un_brouillon_ne_bloque_pas(depot, tmp_path):
    (depot / "contenu" / "partie9.py").write_text(
        'from moteur.blocs import video\nCORPS = {"p1-suite": video("absente.mp4", "Une vidéo à tourner", "3 min")}\n',
        encoding="utf-8")
    construire(depot, tmp_path / "site")
    construire(depot, tmp_path / "apercu", brouillons=True)


# — cles.lock (M2, E3) : une clé publiée ne disparaît jamais —

def remplacer(fichier, ancien, nouveau):
    fichier.write_text(fichier.read_text(encoding="utf-8").replace(ancien, nouveau), encoding="utf-8")


def test_renommer_une_cle_publiee_fait_echouer_la_construction(depot, tmp_path):
    """La preuve de M2. p1-depart est publiée ; on la renomme partout (registre, prérequis, cours) :
    le registre reste cohérent, seul cles.lock voit que la clé publiée a disparu."""
    remplacer(depot / "contenu" / "registre.py", '"p1-depart"', '"p1-commencer"')
    remplacer(depot / "contenu" / "partie1.py", '"p1-depart"', '"p1-commencer"')
    assert refus(depot, tmp_path) == (
        "Clés publiées (cles.lock) :\n"
        "  - la clé publiée p1-depart a disparu du registre (étape supprimée ou renommée) : une clé publiée "
        "ne change jamais, remets l'étape p1-depart dans contenu/registre.py\n"
        "  - p1-commencer est publiée mais n'est pas dans cles.lock : lance « moteur verifier --maj-cles »")
    assert not (tmp_path / "site").exists()                          # rien n'est écrit


def test_supprimer_une_etape_publiee_fait_echouer_la_construction(depot, tmp_path):
    remplacer(depot / "contenu" / "registre.py",
              'E("p1-depart", "Le départ", 20, "Savoir commencer.", statut="publie"),', "")
    remplacer(depot / "contenu" / "registre.py", '["p1-depart"], ', "")
    (depot / "contenu" / "partie1.py").write_text("CORPS = {}\n", encoding="utf-8")
    assert "la clé publiée p1-depart a disparu du registre" in refus(depot, tmp_path)


def test_la_commande_construire_echoue_aussi(depot, capsys):
    remplacer(depot / "contenu" / "registre.py", '"p1-depart"', '"p1-commencer"')
    remplacer(depot / "contenu" / "partie1.py", '"p1-depart"', '"p1-commencer"')
    assert cli.principal(["construire", "--dossier", str(depot)]) == cli.ECHEC
    assert "la clé publiée p1-depart a disparu du registre" in capsys.readouterr().err


def test_publier_sans_ajouter_la_cle_refuse(depot, tmp_path):
    rediger_p1_suite(depot, "verifie")
    remplacer(depot / "contenu" / "registre.py", 'statut="verifie"', 'statut="publie"')
    assert refus(depot, tmp_path) == ("Clés publiées (cles.lock) :\n  - p1-suite est publiée mais n'est pas "
                                      "dans cles.lock : lance « moteur verifier --maj-cles »")


def test_publie_sans_cles_lock_refuse(depot, tmp_path):
    (depot / "cles.lock").unlink()
    assert refus(depot, tmp_path) == ("Clés publiées (cles.lock) :\n  - des étapes sont publiées mais cles.lock "
                                      "n'existe pas : lance « moteur verifier --maj-cles »")


def test_sans_etape_publiee_cles_lock_facultatif(depot, tmp_path):
    (depot / "cles.lock").unlink()
    remplacer(depot / "contenu" / "registre.py", ', statut="publie"', "")
    construire(depot, tmp_path / "site")


def test_depublier_reste_permis(depot, tmp_path):
    # p1-depart repasse en brouillon : sa clé reste dans cles.lock et l'étape dans le registre.
    remplacer(depot / "contenu" / "registre.py", ', statut="publie"', "")
    construire(depot, tmp_path / "site")
    assert "Étape en cours de rédaction" in section(lire_page(tmp_path / "site", "chapitre-1.html"), "p1-depart")


def test_cles_lock_illisible_refuse(depot, tmp_path):
    with open(depot / "cles.lock", "a", encoding="utf-8") as f:
        f.write("M3 Insertion\n")
    assert refus(depot, tmp_path) == ("cles.lock, ligne 6 : 'M3 Insertion' n'est pas une clé "
                                      "(minuscules, chiffres et -, 60 au plus)")
