"""Tests du registre : index, numérotation, pages des parties, contrôle des prérequis."""
from moteur.registre import Etape as E, Partie, Parcours


def petit_parcours():
    return Parcours([
        Partie(0, "Pourquoi", "Résumé 0", [
            E("a", "Étape A", 20, "Savoir A"),
            E("b", "Étape B", 25, "Savoir B", ["a"]),
        ]),
        Partie(1, "Mesurer", "Résumé 1", [
            E("c", "Étape C", 30, "Savoir C", ["a", "b"], examen="Annale 2025, ex. 1"),
        ]),
    ])


def test_index_et_numerotation():
    p = petit_parcours()
    assert [e.id for e in p.etapes()] == ["a", "b", "c"]
    assert p.etape("c").titre == "Étape C"
    assert p.partie_de("c").num == 1
    assert p.numero("a") == "0.1"
    assert p.numero("b") == "0.2"
    assert p.numero("c") == "1.1"


def test_fichier_des_parties_selon_le_motif():
    p = petit_parcours()
    assert [x.fichier for x in p.parties] == ["module-0.html", "module-1.html"]
    q = Parcours([Partie(3, "T", "R", [])], motif_fichier="chapitre-{num}.html")
    assert q.parties[0].fichier == "chapitre-3.html"


def test_suites_d_une_etape():
    p = petit_parcours()
    assert [e.id for e in p.suites("a")] == ["b", "c"]
    assert p.suites("c") == []


def test_registre_coherent():
    assert petit_parcours().verifier() == []


def test_prerequis_inconnu():
    p = Parcours([Partie(0, "T", "R", [E("a", "A", 10, "o", ["fantome"])])])
    assert p.verifier() == ["a : prérequis inconnu fantome"]


def test_prerequis_qui_vient_apres():
    p = Parcours([Partie(0, "T", "R", [E("a", "A", 10, "o", ["b"]), E("b", "B", 10, "o")])])
    assert p.verifier() == ["a : le prérequis b vient après"]


def test_prerequis_de_soi_meme_refuse():
    p = Parcours([Partie(0, "T", "R", [E("a", "A", 10, "o", ["a"])])])
    assert p.verifier() == ["a : le prérequis a vient après"]


def test_identifiant_en_double():
    p = Parcours([Partie(0, "T", "R", [E("a", "A", 10, "o")]),
                  Partie(1, "U", "R", [E("a", "A bis", 10, "o")])])
    assert "identifiant d'étape en double : a" in p.verifier()
    # L'index garde la première étape : celle qu'on trouve en lisant le parcours dans l'ordre.
    assert p.etape("a").titre == "A"


# — statuts (M2) —

import pytest

from moteur.registre import BROUILLON, PUBLIE, STATUTS, VERIFIE, ErreurStatut


def test_statut_brouillon_par_defaut():
    e = E("a", "A", 10, "o")
    assert e.statut == BROUILLON
    assert not e.publiee


def test_les_trois_statuts():
    assert STATUTS == ("brouillon", "verifie", "publie")
    assert E("a", "A", 10, "o", statut=VERIFIE).statut == "verifie"
    assert E("a", "A", 10, "o", statut=PUBLIE).publiee


@pytest.mark.parametrize("statut", ["publié", "vérifié", "Publie", "publiee", ""])
def test_statut_inconnu_refuse(statut):
    with pytest.raises(ErreurStatut) as err:
        E("m3-insertion", "A", 10, "o", statut=statut)
    assert str(err.value) == ("étape m3-insertion : statut inconnu %r (attendu : brouillon, verifie, publie)"
                              % statut)


def test_statut_se_donne_par_son_nom():
    # 8ᵉ argument positionnel refusé : « statut= » se lit sans ambiguïté dans le registre.
    with pytest.raises(TypeError):
        E("a", "A", 10, "o", [], None, None, "publie")


def test_verifie_ou_publie_sans_cours_refuse():
    p = Parcours([Partie(0, "T", "R", [
        E("a", "A", 10, "o"),                       # brouillon sans cours : normal
        E("b", "B", 10, "o", statut=VERIFIE),
        E("c", "C", 10, "o", statut=PUBLIE),
    ])])
    assert p.verifier_statuts() == ["b : statut verifie, mais son cours n'est pas écrit",
                                    "c : statut publie, mais son cours n'est pas écrit"]
    p.etape("b").corps = "<p>relu</p>"
    p.etape("c").corps = "<p>publié</p>"
    p.etape("a").corps = "<p>en cours</p>"         # brouillon avec cours : normal aussi
    assert p.verifier_statuts() == []
