"""Tests de « moteur verifier » (moteur/verifier.py) sur une copie du parcours d'exemple."""
import shutil
from pathlib import Path

import pytest

from moteur import cli
from moteur.chargement import ErreurConstruction
from moteur.sorties.site import construire

EXEMPLE = Path(__file__).parent / "exemple"


@pytest.fixture
def depot(tmp_path):
    d = tmp_path / "parcours"
    shutil.copytree(EXEMPLE, d)
    return d


def remplacer(fichier, ancien, nouveau):
    texte = fichier.read_text(encoding="utf-8")
    assert ancien in texte
    fichier.write_text(texte.replace(ancien, nouveau), encoding="utf-8")


def publier(depot, eid, corps):
    """Donne un cours à l'étape eid et la publie (sans toucher à cles.lock)."""
    with open(depot / "contenu" / "partie9.py", "a", encoding="utf-8") as f:
        f.write("CORPS = globals().get('CORPS', {})\nCORPS[%r] = %r\n" % (eid, corps))
    reg = depot / "contenu" / "registre.py"
    texte = reg.read_text(encoding="utf-8")
    debut = texte.index('E("%s"' % eid)
    fin = texte.index("),\n", debut)
    reg.write_text(texte[:fin] + ', statut="publie"' + texte[fin:], encoding="utf-8")


def verifier(depot, capsys, *options):
    code = cli.principal(["verifier", "--dossier", str(depot), *options])
    return code, capsys.readouterr().out


def test_parcours_d_exemple_sans_erreur(depot, capsys):
    code, sortie = verifier(depot, capsys)
    assert code == cli.OK
    assert sortie == ("moteur verifier : 3 étapes (1 publiée(s), 0 vérifiée(s), 2 brouillon(s))\n"
                      "Aucune erreur, 0 avertissement(s).\n")


def test_verifier_n_ecrit_rien(depot, capsys):
    avant = sorted(p.relative_to(depot) for p in depot.rglob("*") if "__pycache__" not in p.parts)
    verifier(depot, capsys)
    apres = sorted(p.relative_to(depot) for p in depot.rglob("*") if "__pycache__" not in p.parts)
    assert avant == apres


def test_cle_publiee_renommee(depot, capsys):
    remplacer(depot / "contenu" / "registre.py", '"p1-depart"', '"p1-commencer"')
    remplacer(depot / "contenu" / "partie1.py", '"p1-depart"', '"p1-commencer"')
    code, sortie = verifier(depot, capsys)
    assert code == cli.ECHEC
    assert "Clés publiées (cles.lock) :" in sortie
    assert "la clé publiée p1-depart a disparu du registre" in sortie
    assert sortie.endswith("2 erreur(s), 0 avertissement(s).\n")


def test_erreur_de_registre(depot, capsys):
    remplacer(depot / "contenu" / "registre.py", '["p1-suite"]', '["inconnue"]')
    code, sortie = verifier(depot, capsys)
    assert code == cli.ECHEC
    assert sortie == ("Erreurs (la construction sera refusée) :\n"
                      "  Registre incohérent :\n    - p2-loin : prérequis inconnu inconnue\n")


def test_maj_cles_ajoute_la_cle_d_une_etape_publiee(depot, capsys):
    publier(depot, "p1-suite", "<p>La suite.</p>")
    assert verifier(depot, capsys)[0] == cli.ECHEC                # pas encore dans cles.lock
    code, sortie = verifier(depot, capsys, "--maj-cles")
    assert code == cli.OK
    assert sortie.startswith("cles.lock : ajoutée(s) : p1-suite\n")
    assert (depot / "cles.lock").read_text(encoding="utf-8").splitlines()[-2:] == ["p1-depart", "p1-suite"]
    assert verifier(depot, capsys, "--maj-cles")[1].startswith("cles.lock : rien à ajouter\n")


def test_maj_cles_ne_repare_pas_une_cle_disparue(depot, capsys):
    remplacer(depot / "contenu" / "registre.py", '"p1-depart"', '"p1-commencer"')
    remplacer(depot / "contenu" / "partie1.py", '"p1-depart"', '"p1-commencer"')
    code, sortie = verifier(depot, capsys, "--maj-cles")
    assert code == cli.ECHEC                                       # p1-commencer ajoutée, p1-depart manque toujours
    assert "la clé publiée p1-depart a disparu du registre" in sortie
    assert "p1-depart" in (depot / "cles.lock").read_text(encoding="utf-8")


def test_avertissement_prerequis_non_publie(depot, capsys):
    publier(depot, "p2-loin", "<p>Loin.</p>")                     # son prérequis p1-suite est un brouillon
    code, sortie = verifier(depot, capsys, "--maj-cles")
    assert code == cli.OK
    assert ("  - p2-loin (publiée) : son prérequis p1-suite n'est pas publié, le lien mène à sa fiche\n"
            "Aucune erreur, 1 avertissement(s).") in sortie


def test_avertissement_video_manquante_dans_un_brouillon(depot, capsys):
    (depot / "contenu" / "partie9.py").write_text(
        'from moteur.blocs import video\nCORPS = {"p1-suite": video("a-tourner.mp4", "Plus tard", "3 min")}\n',
        encoding="utf-8")
    code, sortie = verifier(depot, capsys)
    assert code == cli.OK
    assert "  - p1-suite (brouillon) : vidéo manquante videos/a-tourner.mp4, à ajouter avant de publier" in sortie


def test_video_manquante_dans_une_etape_publiee(depot, capsys):
    (depot / "videos" / "demo.mp4").unlink()
    code, sortie = verifier(depot, capsys)
    assert code == cli.ECHEC
    assert "  Vidéos :\n    - p1-depart : vidéo manquante videos/demo.mp4" in sortie


LIENS = ('<p><a href="chapitre-1.html#p1-depart">ok</a> <a href="#p1-depart">ok</a> '
         '<a href="https://example.org/x">externe</a> <a href="videos/demo.mp4">fichier</a> '
         '<a href="index.html">accueil</a> '
         '<a href="absente.html">page</a> <a href="chapitre-2.html#fantome">ancre</a></p>')


def test_liens_internes_du_cours_publie(depot, capsys):
    publier(depot, "p1-suite", LIENS)
    code, sortie = verifier(depot, capsys, "--maj-cles")
    assert code == cli.ECHEC
    assert ("  Liens :\n"
            "    - p1-suite : lien vers absente.html, mais la page absente.html n'existe pas\n"
            "    - p1-suite : lien vers chapitre-2.html#fantome, mais chapitre-2.html n'a pas d'ancre #fantome\n"
            ) in sortie


def test_liens_d_un_brouillon_non_verifies(depot, capsys):
    (depot / "contenu" / "partie9.py").write_text("CORPS = {'p1-suite': %r}\n" % LIENS, encoding="utf-8")
    assert verifier(depot, capsys)[0] == cli.OK


def test_construire_refuse_les_memes_erreurs(depot, tmp_path, capsys):
    publier(depot, "p1-suite", LIENS)
    verifier(depot, capsys, "--maj-cles")
    with pytest.raises(ErreurConstruction) as err:
        construire(depot, tmp_path / "site")
    assert str(err.value).startswith("Liens :\n  - p1-suite : lien vers absente.html")
    assert not (tmp_path / "site").exists()


def test_construire_annonce_les_avertissements(depot, tmp_path, capsys):
    publier(depot, "p2-loin", "<p>Loin.</p>")
    verifier(depot, capsys, "--maj-cles")
    assert cli.principal(["construire", "--dossier", str(depot), "--sortie", str(tmp_path / "site")]) == cli.OK
    assert capsys.readouterr().out.endswith("1 avertissement(s) : lance « moteur verifier » pour les voir\n")
