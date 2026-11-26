"""Le rendu site de chaque bloc est identique, à l'octet près, à l'ancienne brique de Complexité.

L'oracle est tests/ancien/briques_complexite.py, copie figée de l'ancien contenu/briques.py :
on appelle la même brique des deux côtés, avec les mêmes arguments, et on compare les chaînes.
"""
import pytest

from moteur import blocs as B
from moteur.sorties.site import RENDUS, Rendu
from tests.ancien import briques_complexite as A

TEMPS = ["Comprendre", "Démontrer", "Implémenter", "S'exercer"]

TESTS_ATELIER = [
    {"appel": "f([3, 8, 2, 6])", "verif": "r == ([2, 3, 6, 8], 6)", "attendu": "([2, 3, 6, 8], 6) — l'exemple"},
    {"appel": "f(0)", "leve": "ValueError", "attendu": "une ValueError </script> piège"},
]
CAS_MESURE = [{"nom": "Tableau trié", "court": "trié", "expr": "(list(range(n)),)", "couleur": "meilleur", "essais": 1},
              {"nom": "Au hasard", "court": "hasard", "expr": "(random.sample(range(n), n),)", "couleur": "moyen", "essais": 5}]

# (nom de la brique, arguments) : chaque cas est appelé dans l'ancienne et dans la nouvelle version.
CAS = [
    ("retenir", ("Définition", r"<p>\(f = O(g)\) si … é &amp; <em>x</em></p>")),
    ("demo", ("<p>Par récurrence.</p>",)),
    ("demo", ("<p>x</p>", "Preuve du lemme")),
    ("prof", ("<p>Conseil</p>",)),
    ("prof", ("<p>Conseil</p>", "Attention")),
    ("master", ("<p>RSA</p>",)),
    ("examen", ("<p>Rédige ainsi.</p>",)),
    ("examen", ("<p>x</p>", "Barème")),
    ("code", ("\ndef f(x):\n    return x < 2 and 'é'\n",)),
    ("code", ("print(1)", "sage", "1\n", "Avec Sage")),
    ("exo", (1, "<p>Énoncé</p>", "<p>Corrigé</p>")),
    ("exo", ("2 bis", "<p>E</p>", "<p>C</p>", "<p>Remarque</p>", "★★")),
    ("exercice", (3, "★", r"<p>Calculer \(T(n)\)</p>", "<p>Indice</p>", "<p>Correction</p>")),
    ("exercice", (4, "★★★", "<p>E</p>", "<p>I</p>", "<p>C</p>", "<p>R</p>")),
    ("video_attente", ("le tri fusion",)),
    ("qcm", ("entree", [("Q1 ?", ["a", r"\(n^2\)", "c"], 1, "Parce que."), ("Q2 ?", ["x", "y"], 0, "Car.")])),
    ("qcm", ("sortie", [("Seule ?", ["a", "b"], 1, "Voilà.")])),
    ("qcm", ("sortie", [("Q ?", ["a", "b"], 0, "x")] * 4)),
    ("preuve", ("Théorème", r"<p>\(\sum k = n(n+1)/2\)</p>", "On somme deux fois.", ["Écrire", "Retourner"], "<p>Complète</p>")),
    ("a_toi", ("<p>À faire</p>", "<p>Solution</p>")),
    ("a_retenir", (["Ligne 1", r"\(\Theta(n^2)\)"],)),
    ("atelier", ("tri", "<p>Complète la fonction.</p>", "\ndef f(T):\n    # à toi\n    pass\n", TESTS_ATELIER, "<p>Corrigé</p>")),
    ("atelier", ("vide", "<p>c</p>", "x = 1", [], "<p>c</p>")),
    ("sage_atelier", ("<p>Vérifie.</p>", "\nfactor(2^64 + 1) < 3\n")),
    ("methode", ("analyser une boucle", ["Repérer", "Compter", r"Sommer \(\sum\)"])),
    ("animateur", ("anim-ins", "insertion", [("L'exemple", [3, 8, 2, 6]), ("Trié", [1, 2, 3])], "Le tri pas à pas")),
    ("mesure", ("tri", "<p>Mesure.</p>", "tri_insertion", [10, 100, 1000],
                [("n²/4", "n*n/4"), ("n", "n")], CAS_MESURE)),
    ("mesure", ("tri", "<p>M</p>", "f", [1, 2], [], CAS_MESURE, [("trié / n", 0, "n")], "taille <b>n</b> & co")),
    ("tableau", (["n", "T(n)"], [["1", r"\(0\)"], ["2", "1"]])),
    ("tableau", (["a"], [["x"]], "compact")),
]


@pytest.fixture
def rendu(tmp_path, monkeypatch):
    videos = tmp_path / "docs" / "videos"
    videos.mkdir(parents=True)
    (videos / "avec.vtt").write_text("WEBVTT\n", encoding="utf-8")
    monkeypatch.setattr(A, "_RACINE", str(tmp_path))  # l'ancienne brique video cherchait docs/videos
    return Rendu(TEMPS, str(videos))


@pytest.mark.parametrize("nom,args", CAS, ids=[f"{n}-{i}" for i, (n, _a) in enumerate(CAS)])
def test_rendu_identique_a_l_ancienne_brique(nom, args, rendu):
    assert rendu(getattr(B, nom)(*args)) == getattr(A, nom)(*args)


@pytest.mark.parametrize("fichier", ["avec.mp4", "sans.mp4"])
def test_video_avec_et_sans_sous_titres(fichier, rendu):
    args = (fichier, "Un million de cases <em>vite</em>", "1 min 20")
    assert rendu(B.video(*args)) == A.video(*args)
    assert ("<track" in rendu(B.video(*args))) == (fichier == "avec.mp4")


def test_composition_identique_a_la_concatenation(rendu):
    """Le cours assemble HTML et briques avec + : le rendu de la Suite doit égaler l'ancienne chaîne."""
    def cours(m):
        return ("<p class=\"lead\">Intro</p>" + m.video("avec.mp4", "Légende", "2 min") + "<p>suite</p>"
                + m.a_toi("<p>Remplis :</p>" + m.tableau(["n"], [["1"]]), "<p>sol</p>")
                + m.methode("t", ["a", "b"]))
    assert rendu(cours(B)) == cours(A)


def test_etape_complete_identique(rendu):
    def etape(m):
        entree = m.qcm("entree", [("Q ?", ["a", "b"], 1, "x")])
        sortie = m.qcm("sortie", [("Q ?", ["a", "b"], 0, "x"), ("R ?", ["c", "d"], 1, "y")])
        return m.etape(entree, "<p>C</p>" + m.video("sans.mp4", "L", "1 min"),
                       m.preuve("Lemme", "<p>e</p>", "idée", ["a"], "<p>p</p>"),
                       m.atelier("at", "<p>c</p>", "def f():\n    pass", TESTS_ATELIER, "<p>k</p>"),
                       m.exercice(1, "★", "<p>e</p>", "<p>i</p>", "<p>c</p>"), sortie, m.a_retenir(["x"]))
    assert rendu(etape(B)) == etape(A)


def test_libelle_du_troisieme_temps_reglable(tmp_path):
    r = Rendu(["Comprendre", "Démontrer", "Calculer", "S'exercer"], str(tmp_path))
    html = r(B.etape("", "<p>1</p>", "<p>2</p>", "<p>3</p>", "<p>4</p>", "", ""))
    assert "Calculer</button>" in html and "Temps suivant : Calculer →" in html
    assert "Implémenter" not in html


def test_chaque_classe_de_bloc_a_son_rendu():
    classes = {c for c in vars(B).values() if isinstance(c, type) and issubclass(c, B.Bloc) and c is not B.Bloc}
    # Question n'est rendue qu'à l'intérieur d'un Qcm.
    assert classes - {B.Question} <= RENDUS.keys()


def test_chaine_rendue_telle_quelle(rendu):
    assert rendu("<p>é</p>") == "<p>é</p>"
