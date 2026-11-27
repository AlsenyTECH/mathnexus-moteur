"""Rendu « fragment » (moteur/sorties/fragment.py) : du HTML que la plateforme accepte, sans aucun script.

Chaque cas est passé dans `inspecter_html`, la fonction de la plateforme qui relève tout ce qui
pourrait exécuter du code (moteur/controle.py) : un seul problème et le test échoue.
"""
import pytest

from moteur import blocs as B
from moteur.controle import inspecter_html
from moteur.sorties.fragment import RENDUS, RenduFragment, developper_macros
from tests.test_site_blocs import CAS

TEMPS = ["Comprendre", "Démontrer", "Calculer", "S'exercer"]
URL = "https://alsenytech.github.io/exemple/"
QCM = B.qcm("sortie", [("Combien ?", ["un", r"\(n^2\)", "trois"], 1, "<p>Parce que.</p>")])


def quatre_temps():
    return B.etape(B.qcm("entree", [("Prêt ?", ["oui", "non"], 0, "Bien.")]),
                   "<p>Comprendre</p>" + B.video("demo.mp4", "La démo", "1 min"),
                   B.preuve("Théorème", "<p>E</p>", "Idée", ["a", "b"], "<p>C</p>"),
                   B.atelier("at", "<p>Code.</p>", "def f():\n    pass", [], "<p>Corrigé</p>"),
                   B.exercice(1, "★", "<p>E</p>", "<p>I</p>", "<p>C</p>"), QCM, B.a_retenir(["Une chose"]))


CAS_FRAGMENT = [(nom, getattr(B, nom)(*args)) for nom, args in CAS] + [
    ("video", B.video("demo.mp4", "La démo", "1 min 20")),
    ("etape", quatre_temps()),
    ("suite", "<p>a</p>" + B.retenir("R", "<p>b</p>") + "<p>c</p>"),
]


@pytest.fixture
def rendu(tmp_path):
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "demo.vtt").write_text("WEBVTT\n", encoding="utf-8")
    return RenduFragment(TEMPS, str(videos), URL, {"N": r"\mathbb{N}", "cle": r"\text{clé}"})


def _sous_classes(c):
    for s in c.__subclasses__():
        yield s
        yield from _sous_classes(s)


def test_chaque_bloc_a_un_rendu_fragment():
    # Un nouveau bloc sans rendu fragment ferait échouer le paquet : on le voit ici d'abord.
    # Question n'existe qu'à l'intérieur d'un Qcm.
    assert {c for c in _sous_classes(B.Bloc) if c is not B.Question} <= set(RENDUS)


def test_les_cas_couvrent_chaque_bloc():
    assert {type(b) for _nom, b in CAS_FRAGMENT if not isinstance(b, str)} >= set(RENDUS)


@pytest.mark.parametrize("nom,bloc", CAS_FRAGMENT, ids=[c[0] for c in CAS_FRAGMENT])
def test_aucun_bloc_ne_produit_de_html_refuse_par_la_plateforme(rendu, nom, bloc):
    html = rendu.finir(rendu(bloc))
    assert inspecter_html(html, nom) == []
    assert rendu.problemes == []


def test_quatre_temps_a_la_suite_sans_onglets(rendu):
    html = rendu(quatre_temps())
    assert 'role="tab"' not in html and "hidden" not in html
    assert "<h3>1. Comprendre</h3>" in html and "<h3>3. Calculer</h3>" in html
    assert html.index("Test d'entrée") < html.index("<h3>1. Comprendre</h3>")   # le test d'entrée d'abord


def test_qcm_statique_reponse_dans_un_details(rendu):
    html = rendu(QCM)
    assert 'data-composant="qcm"' in html and "<form" not in html and "<input" not in html
    assert "<details><summary>Voir la réponse</summary><p><b>Réponse b)</b> \\(n^2\\)</p><p>Parce que.</p></details>" in html
    assert "data-bonne" not in html   # la bonne réponse n'est que dans le <details>


def test_atelier_statique(rendu):
    html = rendu(B.atelier("tri", "<p>Complète.</p>", "def f(T):\n    return T < 2", [{"appel": "f(1)"}], "<p>Corrigé</p>"))
    assert 'data-composant="atelier" data-id="tri"' in html
    assert "<pre>def f(T):\n    return T &lt; 2</pre>" in html          # code échappé
    assert "<details><summary>Voir le corrigé (après avoir essayé)</summary><p>Corrigé</p></details>" in html
    assert "<textarea" not in html and "<script" not in html and "f(1)" not in html   # tests cachés : pas dans le fragment


def test_animateur_montre_les_entrees(rendu):
    html = rendu(B.animateur("anim", "insertion", [("L'exemple", [3, 8, 2, 6])], "Le tri pas à pas"))
    assert "<li>L&#x27;exemple : 3, 8, 2, 6</li>" in html and 'data-composant="animateur"' in html


def test_code_sans_bouton_copier(rendu):
    html = rendu(B.code("x = 1"))
    assert "<button" not in html and "<pre>x = 1</pre>" in html


def test_video_lue_depuis_le_site_public(rendu):
    html = rendu(B.video("demo.mp4", "La démo", "1 min"))
    assert 'src="https://alsenytech.github.io/exemple/videos/demo.mp4"' in html
    assert 'src="https://alsenytech.github.io/exemple/videos/demo.vtt"' in html
    assert 'crossorigin="anonymous"' in html   # sous-titres servis par une autre origine


def test_video_sans_url_signalee(tmp_path):
    r = RenduFragment(TEMPS, str(tmp_path))
    r.ou = "p1-depart"
    assert r(B.video("demo.mp4", "La démo", "1 min")) == ""
    assert r.problemes == ["p1-depart : vidéo demo.mp4 : indique l'adresse du site public dans parcours.toml "
                           "([site] url), d'où la plateforme lira la vidéo"]


def test_liens_relatifs_vers_le_site_public(rendu):
    html = rendu.finir('<a href="outils.html#cal">a</a> <a href="#local">b</a> <a href="https://x.org/">c</a>')
    assert '<a href="https://alsenytech.github.io/exemple/outils.html#cal">a</a>' in html
    assert '<a href="#local">b</a>' in html and '<a href="https://x.org/">c</a>' in html


def test_lien_relatif_sans_url_signale(tmp_path):
    r = RenduFragment(TEMPS, str(tmp_path))
    r.finir('<a href="outils.html">a</a>')
    assert len(r.problemes) == 1 and "lien relatif « outils.html »" in r.problemes[0]


def test_macros_developpees_dans_les_formules_seulement(rendu):
    html = rendu.finir(r"<p>\N hors formule, \(x \in \N\), \(\Nombre\), \[\cle_1\]</p>")
    assert r"\N hors formule" in html                       # hors formule : on ne touche pas
    assert r"\(x \in \mathbb{N}\)" in html
    assert r"\(\Nombre\)" in html                           # \Nombre n'est pas la macro \N
    assert r"\[\text{clé}_1\]" in html


def test_macro_qui_en_utilise_une_autre():
    assert developper_macros(r"\(\A\)", {"A": r"\B+1", "B": r"\mathbb{B}"}) == r"\(\mathbb{B}+1\)"


def test_inferieur_protege_dans_les_formules(rendu):
    assert rendu.finir(r"<p>\(a < b\)</p>") == r"<p>\(a \lt  b\)</p>"
