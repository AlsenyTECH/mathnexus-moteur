# CLAUDE.md — mathnexus-moteur

À lire au début de chaque conversation. À mettre à jour à la fin de chaque session (« État » et « Journal »).

## But

Chantier 1 du skill projet-dev : un seul format et un seul générateur pour tous les parcours MathNexus,
avec trois sorties : site statique, **paquet pour la plateforme**, PDF.

- Plan validé (décisions du 26/11/2026) : doc projet « Moteur de contenu — plan » (projet Claude *Dev · Moteur et plateforme*).
- Modèle de départ : `AlsenyTECH/parcours-complexite` (registre + briques + `build.py`).
- **Contrat de format** : `mathnexus-plateforme/backend/contenus/FORMAT_PAQUET.md` et `paquet.py` font autorité.
  Le moteur produit exactement le format 1 et contrôle chaque paquet avec `lire_paquet`, reprise de la plateforme.
  Toute évolution du format commence dans la plateforme.

Alseny construit pour apprendre : il lance lui-même le code et les tests. Expliquer chaque choix.

## Décisions

- Dépôt moteur partagé, installé par pip à une version épinglée (`@vX.Y.Z`) dans chaque dépôt de parcours.
- PDF en LaTeX au style maison (`mathnexus.sty`).
- Vidéos sur Bunny Stream pour tout (site public et plateforme), plus dans Git.
- Sites publiés par une action GitHub ; plus de `docs/` généré dans Git ; archive hors ligne jointe à chaque version.

## Stack

- Python ≥ 3.11, **aucune dépendance à l'exécution** (bibliothèque standard : argparse, html.parser, zipfile, json).
- pytest pour les tests ; CI GitHub Actions sur Python 3.11 et 3.13, avec une installation « comme un dépôt de parcours ».
- Paquet configuré dans `pyproject.toml` (setuptools) ; version lue dans `moteur/__init__.py` (seule source).

## Commandes

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
moteur --help            # ou : python -m moteur --help
```

Publier une version : changer `__version__`, committer, `git tag vX.Y.Z && git push origin vX.Y.Z`.

## Organisation (cible)

```
moteur/
  cli.py           la commande `moteur` (construire, verifier, paquet, pdf)
  registre.py      Parcours > Parties > Étapes, statuts, prérequis          (M1, M2)
  blocs.py         les briques renvoient des objets                         (M1)
  controle.py      lire_paquet reprise de la plateforme                     (M3)
  verifier.py      prérequis, clés stables (cles.lock), liens, vidéos       (M2)
  sorties/         site.py (M1), paquet.py (M3), latex.py (M5)
modele/            style commun, site.js, polices, MathJax, Pyodide         (M1)
composants/        un module JS par composant interactif                    (M4)
latex/             mathnexus.sty, préambules                                (M5)
tests/
```

## Conventions

- Code, noms, messages et tests en **français**.
- Pas de dépendance ajoutée sans en parler : chaque dépendance s'installe dans tous les dépôts de parcours.
- Chaque étape livre une preuve testable (voir le plan) ; les tests passent avant de pousser.
- Paquets reproductibles : même contenu → même archive (dates et ordre des fichiers ZIP fixés).
- Les clés d'étapes publiées ne changent jamais (`cles.lock`, à partir de M2).

## État (au 26/11/2026)

- [x] **M0** : squelette (pyproject, commande `moteur` avec `--version` et l'aide, sous-commandes qui annoncent
      leur étape, tests, CI, README, licence MIT). Version `0.0.1`, pas encore d'étiquette.
- [ ] M1 : extraction depuis Complexité (registre, blocs, sortie site, style) ; site identique avant/après.
- [ ] M2 : statuts brouillon → vérifié → publié + `cles.lock` + `moteur verifier`.
- [ ] M3 : sortie paquet au format 1, contrôlée par `lire_paquet`, importée dans la plateforme locale.
- [ ] M4 : composants partagés + évaluations en données (format suivant, défini d'abord dans la plateforme).
- [ ] M5 : PDF LaTeX.
- [ ] M6 : vidéos Bunny + action GitHub qui envoie le paquet à l'API d'import.

## Journal

- 26/11/2026 — M0 : squelette créé, 10 tests passent sur Python 3.11 et 3.13, installation pip vérifiée dans un environnement neuf.
