"""Sortie paquet (moteur/sorties/paquet.py et « moteur paquet ») : la preuve de M3.

- chaque paquet construit passe lire_paquet, la fonction de la plateforme (moteur/controle.py) ;
- un paquet que la plateforme refuserait fait échouer la construction, sans rien écrire ;
- deux constructions du même contenu donnent la même archive, donc la même empreinte.
"""
import hashlib
import io
import json
import os
import shutil
import zipfile
from pathlib import Path

import pytest

from moteur import cli
from moteur.chargement import ErreurConstruction
from moteur.controle import lire_paquet
from moteur.sorties.paquet import cle_partie, construire, ecrire_zip

EXEMPLE = Path(__file__).resolve().parent / "exemple"


@pytest.fixture
def depot(tmp_path):
    """Une copie du parcours d'exemple, qu'un test peut abîmer sans gêner les autres."""
    d = tmp_path / "parcours"
    shutil.copytree(EXEMPLE, d)
    return d


def remplacer(fichier, ancien, nouveau):
    texte = fichier.read_text(encoding="utf-8")
    assert ancien in texte
    fichier.write_text(texte.replace(ancien, nouveau), encoding="utf-8")


def refus(depot, tmp_path):
    with pytest.raises(ErreurConstruction) as err:
        construire(depot, tmp_path / "p.zip")
    assert not (tmp_path / "p.zip").exists()          # rien n'est écrit
    return str(err.value)


# — la preuve de M3 —

def test_chaque_paquet_passe_lire_paquet(depot, tmp_path):
    paquet, chemin, _ = construire(depot, tmp_path / "p.zip")
    donnees = Path(chemin).read_bytes()
    lu = lire_paquet(donnees)                         # relu comme le ferait la plateforme
    assert lu.empreinte == paquet.empreinte == hashlib.sha256(donnees).hexdigest()
    assert (lu.slug, lu.titre, lu.matiere, lu.cycle) == (
        "exemple-moteur", "Parcours Exemple du moteur", "Mathématiques", "universite")
    etape = lu.parties[0].etapes[0]
    assert (etape.cle, etape.acces, etape.duree_min) == ("p1-depart", "public", 20)
    assert etape.html.startswith('<p class="objectif">Savoir commencer.</p>')


def test_paquet_refuse_fait_echouer_la_construction(depot, tmp_path, capsys):
    # Du HTML que le site accepte, mais pas la plateforme : un bouton avec un gestionnaire d'événement.
    remplacer(depot / "contenu" / "partie1.py", '"<p>Calcul.</p>"', '"<button onclick=\\"go()\\">Calcul</button>"')
    message = refus(depot, tmp_path)
    assert message.startswith("Paquet refusé par le contrôle de la plateforme (moteur/controle.py)")
    assert "etapes/p1-depart.html, ligne 1 : balise <button> interdite" in message
    assert "attribut onclick interdit (gestionnaire d'événement)" in message
    # Et la commande s'arrête avec le code 1.
    assert cli.principal(["paquet", "--dossier", str(depot), "--sortie", str(tmp_path / "p.zip")]) == cli.ECHEC
    assert "balise <button> interdite" in capsys.readouterr().err


def test_deux_constructions_meme_empreinte(depot, tmp_path):
    # Deux copies du même contenu, à deux endroits, avec des dates de fichiers différentes.
    autre = tmp_path / "autre"
    shutil.copytree(depot, autre)
    for f in autre.rglob("*"):
        os.utime(f, (1_000_000_000, 1_000_000_000))
    p1, c1, _ = construire(depot, tmp_path / "un.zip")
    p2, c2, _ = construire(autre, tmp_path / "deux.zip")
    assert Path(c1).read_bytes() == Path(c2).read_bytes()
    assert p1.empreinte == p2.empreinte


def test_archive_type_meme_octets_sur_toute_machine():
    # Empreinte figée : la CI la vérifie sous Linux et Windows, Python 3.11 et 3.13.
    # Si ce test casse après une mise à jour de Python, le paquet n'est plus reproductible d'une machine à l'autre.
    donnees = ecrire_zip({"etapes/b.html": "<p>é</p>".encode(), "manifeste.json": b'{"format": 1}\n',
                          "etapes/a.html": b"<p>a</p>"})
    assert hashlib.sha256(donnees).hexdigest() == "1c9c3b10664ec6cb66c09368cd33d7c41f35bfaa80025120ff869d17420dd62d"


def test_entrees_dans_un_ordre_fixe_datees_et_stockees():
    z = zipfile.ZipFile(io.BytesIO(ecrire_zip({"etapes/z.html": b"z", "etapes/a.html": b"a", "manifeste.json": b"{}"})))
    assert z.namelist() == ["manifeste.json", "etapes/a.html", "etapes/z.html"]
    for i in z.infolist():
        assert i.date_time == (1980, 1, 1, 0, 0, 0)
        assert i.compress_type == zipfile.ZIP_STORED and i.create_system == 3


# — ce qui sort —

def test_seules_les_etapes_publiees_sortent(depot, tmp_path):
    paquet, chemin, _ = construire(depot, tmp_path / "p.zip")
    z = zipfile.ZipFile(chemin)
    assert z.namelist() == ["manifeste.json", "etapes/p1-depart.html"]
    m = json.loads(z.read("manifeste.json"))
    assert [p["cle"] for p in m["parties"]] == ["chapitre-1"]      # le chapitre 2 n'a rien de publié
    assert m["parties"][0]["titre"] == "Chapitre 1 · Premiers pas"
    assert paquet.laissees == 2


def test_aucune_etape_publiee_refusee(depot, tmp_path):
    remplacer(depot / "contenu" / "registre.py", 'statut="publie", ', "")
    (depot / "cles.lock").write_text("", encoding="utf-8")
    assert "aucune étape publiée" in refus(depot, tmp_path)


def test_reglages_du_paquet_exiges(depot, tmp_path):
    remplacer(depot / "parcours.toml", 'slug = "exemple-moteur"', "")
    remplacer(depot / "parcours.toml", 'cycle = "universite"', "")
    message = refus(depot, tmp_path)
    assert "[parcours] slug manque dans parcours.toml" in message and "[parcours] cycle manque" in message


def test_video_sans_url_refusee(depot, tmp_path):
    remplacer(depot / "parcours.toml", 'url = "https://alsenytech.github.io/exemple/"', "")
    assert "p1-depart : vidéo demo.mp4 : indique l'adresse du site public" in refus(depot, tmp_path)


def test_memes_controles_que_le_site(depot, tmp_path):
    # Une clé publiée renommée : le paquet est refusé comme le site (cles.lock).
    remplacer(depot / "contenu" / "registre.py", '"p1-depart"', '"p1-commencer"')
    remplacer(depot / "contenu" / "partie1.py", '"p1-depart"', '"p1-commencer"')
    assert "la clé publiée p1-depart a disparu du registre" in refus(depot, tmp_path)


def test_duree_hors_limite_refusee_par_la_plateforme(depot, tmp_path):
    remplacer(depot / "contenu" / "registre.py", '"Le départ", 20,', '"Le départ", 700,')
    assert "duree_min doit être un entier entre 1 et 600" in refus(depot, tmp_path)


@pytest.mark.parametrize("nom,num,cle", [("Module", 0, "module-0"), ("Chapitre", 12, "chapitre-12"),
                                         ("Thème", 2, "theme-2"), ("Séance d'été", 1, "seance-d-ete-1")])
def test_cle_de_partie(nom, num, cle):
    assert cle_partie(nom, num) == cle


def test_commande_paquet(depot, tmp_path, capsys):
    assert cli.principal(["paquet", "--dossier", str(depot)]) == cli.OK
    sortie = capsys.readouterr().out
    chemin = depot / "_paquet" / "exemple-moteur.zip"                # emplacement par défaut
    assert chemin.exists()
    assert "Contrôle de la plateforme (lire_paquet) : accepté" in sortie
    assert "Empreinte SHA-256 : " + hashlib.sha256(chemin.read_bytes()).hexdigest() in sortie
