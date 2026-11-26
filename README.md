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

**M1** (v0.1.0) : la sortie site. Le parcours Complexité est construit par le moteur, et son site est
identique, octet par octet, à celui de l'ancien générateur. Plan complet : doc « Moteur de contenu — plan »
du projet Claude *Dev · Moteur et plateforme*.

## Utiliser le moteur dans un dépôt de parcours

```bash
pip install "mathnexus-moteur @ git+https://github.com/AlsenyTECH/mathnexus-moteur@v0.1.0"
moteur construire                    # construit le site (réglages dans parcours.toml)
moteur comparer ANCIEN NOUVEAU       # deux sites, octet par octet (preuve qu'une montée de version ne change rien)
```

Un dépôt de parcours contient :

```
parcours.toml          les réglages (voir tests/exemple/parcours.toml, commenté)
requirements.txt       la version épinglée du moteur
contenu/registre.py    PARTIES : parties et étapes (from moteur.registre import Etape, Partie)
contenu/*.py           CORPS[identifiant] = etape(…), écrit avec les briques de moteur.blocs
contenu/pages.py       facultatif : pages(site) → les pages propres (accueil, outils)
modele/                facultatif : CSS et JS propres au parcours
```

Les briques (`retenir`, `preuve`, `atelier`…) renvoient des **objets** : `"<p>…</p>" + video(…)` donne une
`Suite`. Le cours garde ainsi sa structure, que chaque sortie rend à sa façon. Un bloc ne se met pas dans
un `%`, une f-string ou un `join` : c'est une erreur, pour que la structure ne se perde jamais en silence.

## Travailler sur le moteur

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"     # -e : les modifications du code sont prises en compte sans réinstaller
python -m pytest            # les tests
moteur --help
```

## Publier une version

1. Changer `__version__` dans `moteur/__init__.py` (par exemple `0.1.0`).
2. Committer, puis poser l'étiquette correspondante : `git tag -a v0.1.0 -m "…" && git push origin v0.1.0`.
3. Dans chaque dépôt de parcours, monter la version épinglée quand on est prêt.

## Licence

Code sous licence MIT (voir `LICENCE`). Le contenu des parcours garde sa propre licence, dans son dépôt.
