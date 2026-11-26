"""Tests de l'étape M0 : la commande existe, donne sa version et annonce les étapes à venir."""
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import moteur
from moteur import cli

RACINE = Path(__file__).resolve().parent.parent


def test_version_est_un_numero_semantique():
    morceaux = moteur.__version__.split(".")
    assert len(morceaux) == 3 and all(m.isdigit() for m in morceaux)


def test_pyproject_lit_la_version_dans_le_paquet():
    # Une seule source pour la version : si quelqu'un l'écrit aussi dans pyproject.toml, ce test casse.
    config = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" in config["project"]["dynamic"]
    assert config["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "moteur.__version__"}


def test_option_version(capsys):
    with pytest.raises(SystemExit) as fin:
        cli.principal(["--version"])
    assert fin.value.code == 0
    assert capsys.readouterr().out.strip() == f"mathnexus-moteur {moteur.__version__}"


def test_sans_commande_affiche_l_aide(capsys):
    assert cli.principal([]) == cli.OK
    sortie = capsys.readouterr().out
    for nom in cli.COMMANDES:
        assert nom in sortie


@pytest.mark.parametrize("nom", sorted(cli.COMMANDES))
def test_chaque_commande_annonce_son_etape(nom, capsys):
    assert cli.principal([nom]) == cli.PAS_ENCORE
    _aide, etape = cli.COMMANDES[nom]
    assert etape in capsys.readouterr().err


def test_commande_inconnue_refusee():
    with pytest.raises(SystemExit) as fin:
        cli.principal(["inventee"])
    assert fin.value.code == 2  # code d'erreur d'usage d'argparse


def test_python_m_moteur():
    # Le même programme, lancé comme un vrai processus.
    resultat = subprocess.run([sys.executable, "-m", "moteur", "--version"],
                              capture_output=True, text=True, cwd=RACINE)
    assert resultat.returncode == 0
    assert moteur.__version__ in resultat.stdout
