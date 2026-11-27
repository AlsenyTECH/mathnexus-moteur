"""Tests du contrôle des paquets (moteur/controle.py, copie de la plateforme) et du contrat (moteur/contrat.py)."""
import io
import json
import zipfile

import pytest

from moteur import contrat
from moteur.controle import PaquetInvalide, inspecter_html, lire_paquet


def zip_de(manifeste, fichiers):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("manifeste.json", json.dumps(manifeste, ensure_ascii=False))
        for nom, contenu in fichiers.items():
            z.writestr(nom, contenu)
    return tampon.getvalue()


MANIFESTE = {
    "format": 1,
    "parcours": {"slug": "exemple", "titre": "Exemple", "matiere": "Mathématiques", "cycle": "universite"},
    "parties": [{"cle": "partie-1", "titre": "Partie 1",
                 "etapes": [{"cle": "e1", "titre": "Étape", "fichier": "etapes/e1.html", "acces": "public",
                             "duree_min": 20}]}],
}


def test_la_copie_est_celle_du_contrat():
    # Si quelqu'un modifie controle.py à la main, ce test casse : la copie doit rester celle de la plateforme.
    assert contrat.empreinte_controle() == contrat.EMPREINTE


def test_la_copie_garde_ses_fins_de_ligne_unix():
    assert b"\r\n" not in contrat.FICHIER_CONTROLE.read_bytes()


def test_paquet_valide_lu():
    lu = lire_paquet(zip_de(MANIFESTE, {"etapes/e1.html": "<p>Bonjour \\(x\\)</p>"}))
    assert lu.slug == "exemple" and lu.parties[0].etapes[0].acces == "public"


def test_paquet_avec_script_refuse():
    with pytest.raises(PaquetInvalide) as err:
        lire_paquet(zip_de(MANIFESTE, {"etapes/e1.html": "<p>x</p>\n<script>alert(1)</script>"}))
    assert "etapes/e1.html, ligne 2 : balise <script> interdite" in err.value.problemes


def test_inspecter_html_detecte_bouton_et_gestionnaire():
    pbs = inspecter_html('<button onclick="x()">ok</button>', "f")
    assert any("<button>" in p for p in pbs) and any("onclick" in p for p in pbs)


class _Reponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_contrat_identique(monkeypatch, capsys):
    donnees = contrat.FICHIER_CONTROLE.read_bytes()
    monkeypatch.setattr(contrat.urllib.request, "urlopen", lambda url, timeout: _Reponse(donnees))
    assert contrat.principal() == contrat.IDENTIQUE
    assert "Contrat respecté" in capsys.readouterr().out


def test_contrat_change(monkeypatch, capsys):
    monkeypatch.setattr(contrat.urllib.request, "urlopen", lambda url, timeout: _Reponse(b"FORMAT_ACTUEL = 2\n"))
    assert contrat.principal() == contrat.CHANGE
    assert "a changé" in capsys.readouterr().err


def test_contrat_injoignable(monkeypatch):
    def refus(url, timeout):
        raise OSError("pas de réseau")
    monkeypatch.setattr(contrat.urllib.request, "urlopen", refus)
    assert contrat.principal() == contrat.INJOIGNABLE
