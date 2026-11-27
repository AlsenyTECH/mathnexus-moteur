"""Tests de cles.lock : lecture, écriture, contrôle, mise à jour (moteur/cles.py)."""
import pytest

from moteur import cles
from moteur.registre import Etape as E, Parcours, Partie


def parcours(*statuts):
    """Un parcours d'étapes e1, e2… avec ces statuts ; chaque étape a un cours."""
    p = Parcours([Partie(1, "T", "R", [E("e%d" % (i + 1), "T", 10, "o", statut=st)
                                       for i, st in enumerate(statuts)])])
    for e in p.etapes():
        e.corps = "<p>cours</p>"
    return p


def test_lire_sans_fichier(tmp_path):
    assert cles.lire(tmp_path) is None


def test_lire_ignore_commentaires_et_lignes_vides(tmp_path):
    (tmp_path / "cles.lock").write_text("# entête\n\nm0-attaque\n  m3-insertion  \n# fin\n", encoding="utf-8")
    assert cles.lire(tmp_path) == {"m0-attaque", "m3-insertion"}


def test_lire_fichier_aux_fins_de_ligne_windows(tmp_path):
    (tmp_path / "cles.lock").write_bytes(b"# x\r\nm0-attaque\r\n")
    assert cles.lire(tmp_path) == {"m0-attaque"}


@pytest.mark.parametrize("ligne", ["M0-attaque", "-m0", "m0 attaque", "m0_attaque", "é1", "a" * 61])
def test_lire_refuse_une_ligne_qui_n_est_pas_une_cle(tmp_path, ligne):
    (tmp_path / "cles.lock").write_text("# x\n" + ligne + "\n", encoding="utf-8")
    with pytest.raises(cles.ErreurCles) as err:
        cles.lire(tmp_path)
    assert str(err.value).startswith("cles.lock, ligne 2 : %r n'est pas une clé" % ligne)


def test_ecrire_trie_et_garde_des_fins_de_ligne_unix(tmp_path):
    cles.ecrire(tmp_path, {"m3-insertion", "m0-attaque"})
    octets = (tmp_path / "cles.lock").read_bytes()
    assert b"\r" not in octets
    assert octets == (cles.ENTETE + "m0-attaque\nm3-insertion\n").encode("utf-8")
    assert cles.lire(tmp_path) == {"m0-attaque", "m3-insertion"}


def test_controler_tout_va_bien():
    assert cles.controler(parcours("publie", "brouillon"), {"e1"}) == []


def test_controler_sans_publication_ni_fichier():
    assert cles.controler(parcours("brouillon", "verifie"), None) == []


def test_controler_une_cle_disparue_meme_si_rien_n_est_publie():
    pbs = cles.controler(parcours("brouillon"), {"e1", "ancienne"})
    assert pbs == ["la clé publiée ancienne a disparu du registre (étape supprimée ou renommée) : une clé "
                   "publiée ne change jamais, remets l'étape ancienne dans contenu/registre.py"]


def test_controler_une_cle_publiee_hors_format():
    p = Parcours([Partie(1, "T", "R", [E("Etape_1", "T", 10, "o", statut="publie")])])
    p.etape("Etape_1").corps = "<p>x</p>"
    assert cles.controler(p, {"x"})[0].startswith("Etape_1 : cette clé ne peut pas être publiée")


def test_a_ajouter_dans_l_ordre_du_parcours():
    assert cles.a_ajouter(parcours("publie", "brouillon", "publie"), {"e1"}) == ["e3"]
    assert cles.a_ajouter(parcours("publie", "publie"), None) == ["e1", "e2"]


def test_mettre_a_jour_cree_puis_ajoute_sans_retirer(tmp_path):
    assert cles.mettre_a_jour(tmp_path, parcours("publie", "brouillon")) == ["e1"]
    assert cles.lire(tmp_path) == {"e1"}
    # e1 dépubliée, e2 publiée : e2 s'ajoute, e1 reste.
    assert cles.mettre_a_jour(tmp_path, parcours("brouillon", "publie")) == ["e2"]
    assert cles.lire(tmp_path) == {"e1", "e2"}


def test_mettre_a_jour_ne_reecrit_pas_un_fichier_a_jour(tmp_path):
    (tmp_path / "cles.lock").write_text("# écrit à la main\ne1\n", encoding="utf-8")
    assert cles.mettre_a_jour(tmp_path, parcours("publie")) == []
    assert (tmp_path / "cles.lock").read_text(encoding="utf-8") == "# écrit à la main\ne1\n"


def test_mettre_a_jour_sans_publication_ne_cree_rien(tmp_path):
    assert cles.mettre_a_jour(tmp_path, parcours("brouillon")) == []
    assert not (tmp_path / "cles.lock").exists()
