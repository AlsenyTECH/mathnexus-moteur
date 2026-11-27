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
identique, octet par octet, à celui de l'ancien générateur.

**M2** (v0.2.0) : statuts des étapes (brouillon → vérifié → publié), `cles.lock` et `moteur verifier`. Plan complet : doc « Moteur de contenu — plan »
du projet Claude *Dev · Moteur et plateforme*.

## Utiliser le moteur dans un dépôt de parcours

```bash
pip install "mathnexus-moteur @ git+https://github.com/AlsenyTECH/mathnexus-moteur@v0.2.0"
moteur verifier                      # tous les contrôles, sans rien construire
moteur verifier --maj-cles           # après avoir publié une étape : ajoute sa clé à cles.lock
moteur construire                    # construit le site (réglages dans parcours.toml)
moteur construire --brouillons       # aperçu pour relire, avec le cours non publié, dans _apercu/
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
cles.lock              les clés des étapes publiées (écrit par moteur verifier --maj-cles)
```

### Statuts et clés publiées

Chaque étape a un statut, écrit dans le registre : `E("m3-insertion", …, statut="publie")`.

| Statut | Sens | Sur le site |
| --- | --- | --- |
| `brouillon` (par défaut) | en cours d'écriture | la fiche de l'étape |
| `verifie` | cours relu, nombres vérifiés : prêt à sortir | la fiche de l'étape |
| `publie` | le cours sort | le cours |

Une étape vérifiée ou publiée doit avoir son cours. Une étape publiée a une **clé** (son identifiant) à laquelle
la plateforme accroche la progression des élèves : elle ne doit jamais disparaître ni changer de nom.
`cles.lock` garde la liste des clés publiées ; la construction refuse une clé de la liste absente du registre,
et une étape publiée absente de la liste. Pour publier : passer l'étape en `statut="publie"`, lancer
`moteur verifier --maj-cles`, committer `cles.lock` avec le registre. Dépublier reste permis (la clé reste).

`moteur verifier` et `moteur construire` font les mêmes contrôles : registre, statuts, `cles.lock`, vidéos et
liens internes du cours publié. Les avertissements (prérequis non publié, vidéo manquante dans un brouillon)
ne bloquent pas.

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

1. Changer `__version__` dans `moteur/__init__.py` (par exemple `0.2.0`).
2. Committer, puis poser l'étiquette correspondante : `git tag -a v0.2.0 -m "…" && git push origin v0.2.0`.
3. Dans chaque dépôt de parcours, monter la version épinglée quand on est prêt.

## Licence

Code sous licence MIT (voir `LICENCE`). Le contenu des parcours garde sa propre licence, dans son dépôt.
