"""Tests de `moteur comparer` : la moindre différence entre deux sites doit être trouvée."""
import shutil

import pytest

from moteur.comparer import comparer


@pytest.fixture
def deux_sites(tmp_path):
    a = tmp_path / "ancien"
    (a / "assets" / "fonts").mkdir(parents=True)
    (a / "videos").mkdir()  # dossier vide : il compte aussi
    # write_bytes : sous Windows, write_text changerait \n en \r\n.
    (a / "index.html").write_bytes(b"<p>Accueil</p>\n")
    (a / "assets" / "style.css").write_bytes(b"body{}\n")
    (a / "assets" / "fonts" / "f.woff2").write_bytes(bytes(range(256)))
    b = tmp_path / "nouveau"
    shutil.copytree(a, b)
    return a, b


def test_sites_identiques(deux_sites):
    e = comparer(*deux_sites)
    assert e.identiques()
    assert e.rapport() == "Sites identiques."


def test_un_octet_change(deux_sites):
    a, b = deux_sites
    donnees = bytearray((b / "assets" / "fonts" / "f.woff2").read_bytes())
    donnees[100] ^= 1  # même taille, un seul bit change
    (b / "assets" / "fonts" / "f.woff2").write_bytes(bytes(donnees))
    e = comparer(a, b)
    assert e.differents == ["assets/fonts/f.woff2"]
    assert not e.identiques()


def test_fin_de_ligne_differente(deux_sites):
    a, b = deux_sites
    (b / "index.html").write_bytes(b"<p>Accueil</p>\r\n")
    assert comparer(a, b).differents == ["index.html"]


def test_fichier_manquant_et_en_trop(deux_sites):
    a, b = deux_sites
    (b / "index.html").unlink()
    (b / "nouvelle.html").write_text("x", encoding="utf-8")
    e = comparer(a, b)
    assert e.manquants == ["index.html"]
    assert e.en_trop == ["nouvelle.html"]
    assert "Manquants dans le nouveau (1)" in e.rapport()


def test_dossier_vide_manquant(deux_sites):
    a, b = deux_sites
    (b / "videos").rmdir()
    assert comparer(a, b).manquants == ["videos/"]


def test_dossier_introuvable(tmp_path):
    with pytest.raises(FileNotFoundError):
        comparer(tmp_path / "rien", tmp_path)
