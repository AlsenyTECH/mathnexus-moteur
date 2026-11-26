"""Tests des blocs : des objets qu'on assemble avec +, sans jamais redevenir des chaînes en silence."""
import dataclasses

import pytest

from moteur import blocs as B


def test_une_brique_renvoie_un_objet_avec_ses_donnees():
    v = B.video("m3-insertion.mp4", "Le tri au tableau", "7 min 41")
    assert isinstance(v, B.Video)
    assert (v.fichier, v.legende, v.duree) == ("m3-insertion.mp4", "Le tri au tableau", "7 min 41")


def test_plus_donne_une_suite_dans_l_ordre():
    v = B.video("a.mp4", "L", "1 min")
    s = "<p>avant</p>" + v + "<p>après</p>"
    assert isinstance(s, B.Suite)
    assert s.morceaux == ("<p>avant</p>", v, "<p>après</p>")


def test_suites_aplaties_et_chaines_vides_retirees():
    r = B.retenir("Clé", "<p>x</p>")
    v = B.video("a.mp4", "L", "1 min")
    s = ("<p>1</p>" + r) + ("" + v + "<p>2</p>")
    assert s.morceaux == ("<p>1</p>", r, v, "<p>2</p>")
    assert B.assembler("<p>1</p>", r, v, "<p>2</p>") == s


def test_un_bloc_n_est_pas_une_chaine():
    r = B.retenir("Clé", "<p>x</p>")
    with pytest.raises(TypeError, match="pas une chaîne"):
        "<div>%s</div>" % r
    with pytest.raises(TypeError, match="pas une chaîne"):
        f"<div>{r}</div>"
    with pytest.raises(TypeError):
        "".join(["<p>a</p>", r])


def test_morceau_invalide_refuse():
    with pytest.raises(TypeError, match="texte \\(HTML\\) ou un bloc"):
        B.retenir("Clé", "x") + 3
    with pytest.raises(TypeError):
        B.assembler("<p>a</p>", ["liste"])


def test_les_blocs_ne_changent_plus():
    t = B.tableau(["n", "T(n)"], [["1", "0"], ["2", "1"]])
    assert t.lignes == (("1", "0"), ("2", "1"))  # listes devenues tuples
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.classe = "autre"


def test_qcm_garde_les_questions_en_donnees():
    q = B.qcm("sortie", [("Combien ?", ["1", "2", "3"], 1, "Parce que."),
                         ("Et là ?", ["oui", "non"], 0, "Évident.")])
    assert q.role == "sortie"
    assert q.questions[0] == B.Question("Combien ?", ("1", "2", "3"), 1, "Parce que.")
    assert q.seuil == 1                      # sortie : une erreur permise
    assert B.qcm("entree", [("Q", ["a", "b"], 0, "x")] * 3).seuil == 3   # entrée : tout juste


def test_qcm_refuse_les_erreurs_d_ecriture():
    with pytest.raises(ValueError, match="rôle"):
        B.qcm("milieu", [("Q", ["a"], 0, "x")])
    with pytest.raises(ValueError, match="n'existe pas"):
        B.qcm("sortie", [("Q", ["a", "b"], 2, "x")])
    with pytest.raises(ValueError, match="au moins une question"):
        B.qcm("sortie", [])


def test_parcourir_trouve_les_blocs_imbriques_mais_pas_les_donnees():
    v = B.video("a.mp4", "La légende", "1 min")
    t = B.tableau(["n"], [["1"]])
    etape = B.etape(B.qcm("entree", [("Q", ["a", "b"], 0, "x")]),
                    "<p>c</p>" + v, "<p>d</p>", B.atelier("at", "<p>consigne</p>", "def f(): pass", [], "<p>corrigé</p>"),
                    B.a_toi("<p>e</p>" + t, "<p>s</p>"), "<p>sortie</p>", B.a_retenir(["l1", "l2"]))
    noeuds = list(B.parcourir(etape))
    assert v in noeuds and t in noeuds
    textes = [n for n in noeuds if isinstance(n, str)]
    assert "La légende" in textes and "l2" in textes and "<p>corrigé</p>" in textes
    # Les données des outils (identifiant, code de départ, nom de fichier, rôle) ne sont pas du cours.
    for donnee in ("at", "def f(): pass", "a.mp4", "entree"):
        assert donnee not in textes


def test_chaque_brique_publique_renvoie_un_bloc():
    exemples = [
        B.retenir("L", "c"), B.demo("c"), B.prof("c"), B.master("c"), B.examen("c"),
        B.methode("t", ["a"]), B.a_retenir(["a"]), B.a_toi("e", "s"),
        B.preuve("Théorème", "e", "i", ["a"], "c"), B.exercice(1, "★", "e", "i", "c"),
        B.exo(1, "e", "c"), B.qcm("sortie", [("Q", ["a"], 0, "x")]),
        B.etape("", "", "", "", "", "", ""), B.code("x = 1"), B.tableau(["a"], [["1"]]),
        B.video("a.mp4", "L", "1 min"), B.video_attente("s"),
        B.atelier("id", "c", "d", [], "c"), B.sage_atelier("c", "d"),
        B.animateur("id", "insertion", [("n", [1])], "L"),
        B.mesure("id", "c", "f", [1], [], []),
    ]
    assert all(isinstance(b, B.Bloc) for b in exemples)
