"""Réglages et registre ajoutés pour le paquet (M3) : slug, matière, cycle, url du site, accès des étapes."""
import pytest

from moteur.registre import ACCES, Etape as E, ErreurStatut
from moteur.reglages import ErreurReglages, lire

BASE = '[parcours]\ntitre = "T"\ntitre_long = "T long"\n'


def test_sans_identite_le_site_se_construit_toujours():
    r = lire(BASE)
    assert (r.slug, r.matiere, r.cycle, r.url) == ("", "", "", "")


def test_identite_lue():
    r = lire(BASE + 'slug = "complexite-algorithmes"\nmatiere = "Informatique"\ncycle = "universite"\n'
                    '[site]\nurl = "https://alsenytech.github.io/parcours-complexite"\n')
    assert (r.slug, r.matiere, r.cycle) == ("complexite-algorithmes", "Informatique", "universite")
    assert r.url == "https://alsenytech.github.io/parcours-complexite/"   # « / » final ajouté


@pytest.mark.parametrize("slug", ["Complexite", "-debut", "avec espace", "é", "x" * 61])
def test_slug_invalide_refuse(slug):
    with pytest.raises(ErreurReglages, match="slug"):
        lire(BASE + 'slug = "%s"\n' % slug)


def test_cycle_invalide_refuse():
    with pytest.raises(ErreurReglages, match="cycle « master » invalide"):
        lire(BASE + 'cycle = "master"\n')


@pytest.mark.parametrize("url", ["http://exemple.org/", "exemple.org", "https://a b/"])
def test_url_invalide_refusee(url):
    with pytest.raises(ErreurReglages, match="url"):
        lire(BASE + '[site]\nurl = "%s"\n' % url)


def test_acces_par_defaut_inscrit():
    assert E("e1", "T", 10, "o").acces == "inscrit"
    assert ACCES == ("public", "inscrit", "premium")


def test_acces_donne_par_son_nom():
    assert E("e1", "T", 10, "o", statut="publie", acces="public").acces == "public"


def test_acces_inconnu_refuse_a_la_lecture():
    with pytest.raises(ErreurStatut, match="accès inconnu 'publique'"):
        E("e1", "T", 10, "o", acces="publique")
