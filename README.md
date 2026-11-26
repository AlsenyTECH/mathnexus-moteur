# mathnexus-moteur

Le moteur de contenu des parcours MathNexus : **un format d'écriture, un générateur, trois sorties**.

| Sortie | Pour qui | Étape |
| --- | --- | --- |
| Site statique (GitHub Pages) | le public, hors ligne compris | M1 |
| Paquet pour la plateforme Mathnexus (format 1) | les élèves inscrits | M3 |
| PDF au style maison (LaTeX) | l'impression | M5 |

Chaque parcours vit dans son propre dépôt (`parcours-complexite`, `mathnexus-terminale`…) et installe
le moteur à une version épinglée. Une mise à jour du moteur ne casse donc aucun parcours : chacun passe
à la nouvelle version quand on le décide.

## État

**M0** : squelette. La commande `moteur` existe, donne sa version et annonce l'étape qui livrera chaque
sous-commande. Plan complet : doc « Moteur de contenu — plan » du projet Claude *Dev · Moteur et plateforme*.

## Utiliser le moteur dans un dépôt de parcours

```bash
# première étiquette prévue à la fin de M1 ; d'ici là, @main
pip install "mathnexus-moteur @ git+https://github.com/AlsenyTECH/mathnexus-moteur@v0.1.0"
moteur --version
moteur construire      # à partir de M1
```

## Travailler sur le moteur

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"     # -e : les modifications du code sont prises en compte sans réinstaller
python -m pytest            # les tests
moteur --help
```

## Publier une version

1. Changer `__version__` dans `moteur/__init__.py` (par exemple `0.1.0`).
2. Committer, puis poser l'étiquette correspondante : `git tag v0.1.0 && git push origin v0.1.0`.
3. Dans chaque dépôt de parcours, monter la version épinglée quand on est prêt.

## Licence

Code sous licence MIT (voir `LICENCE`). Le contenu des parcours garde sa propre licence, dans son dépôt.
