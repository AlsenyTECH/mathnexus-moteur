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
- pytest pour les tests ; CI GitHub Actions sur Linux et **Windows** (Alseny travaille sous Windows), Python 3.11 et 3.13,
  avec une installation « comme un dépôt de parcours » (Linux).
- Paquet configuré dans `pyproject.toml` (setuptools) ; version lue dans `moteur/__init__.py` (seule source).

## Commandes

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
moteur --help            # ou : python -m moteur --help
moteur verifier --dossier tests/exemple                        # tous les contrôles, sans construire
moteur construire --dossier tests/exemple --sortie /tmp/site   # le parcours d'exemple
moteur construire --brouillons                                 # aperçu avec le cours non publié (_apercu/)
moteur comparer ANCIEN NOUVEAU                                 # deux sites, octet par octet
moteur verifier --maj-cles                                     # ajoute les clés publiées à cles.lock
```

Sous Windows (invite de commandes) : `py -m venv .venv`, puis `.venv\Scripts\activate`.

Publier une version : changer `__version__`, committer, `git tag -a vX.Y.Z -m "…" && git push origin vX.Y.Z`.
**Les étiquettes sont posées par Alseny** : les sessions Claude ne peuvent pas pousser d'étiquette (refus 403 du proxy).

## Organisation

```
moteur/
  cli.py           la commande `moteur` : construire, comparer (M1), verifier (M2) ; paquet, pdf annoncés
  registre.py      Parcours > Parties > Étapes, index, numérotation, prérequis (M1) ; statuts (M2)
  blocs.py         les briques renvoient des objets (dataclasses figées), + → Suite, parcourir()  (M1)
  reglages.py      parcours.toml (tomllib), clés inconnues refusées               (M1)
  chargement.py    registre, cours (CORPS), pages propres ; refuse registre et statuts incohérents
  cles.py          cles.lock : lire, écrire, controler, mettre_a_jour (ajoute seulement)   (M2)
  verifier.py      contrôles partagés par verifier et construire : cles.lock, vidéos, liens ;
                   avertissements (prérequis non publié, vidéo manquante d'un brouillon)    (M2)
  comparer.py      deux sites octet par octet                                      (M1)
  sorties/site.py  une fonction de rendu par classe de bloc, pages, assets (M1) ; cours des seules
                   étapes publiées, aperçu --brouillons (M2)
  modele/          style commun, site.js, outils.js, atelier(-worker).js, mesure.js, vendor/
                   (MathJax, polices, Pyodide) : installé avec le paquet (package-data)   (M1)
  controle.py      lire_paquet reprise de la plateforme                           (M3)
  sorties/         paquet.py (M3), latex.py (M5)
composants/        un module JS par composant interactif                          (M4)
latex/             mathnexus.sty, préambules                                      (M5)
tests/
  ancien/          copie figée des briques de Complexité : oracle des tests de rendu (ne pas modifier)
  exemple/         parcours d'exemple complet (parcours.toml commenté, cles.lock), construit par les tests et la CI
```

Les JS du modèle portent deux marqueurs remplacés à la copie : `__PREFIXE__` (réglage `prefixe_stockage` :
tous les sites partagent l'origine alsenytech.github.io) et `'__ACCUEIL_VIDE__'` (réglage `message_accueil_vide`).
`.gitattributes` interdit toute conversion de fin de ligne dans `moteur/modele/` (sites identiques à l'octet).

## Conventions

- Code, noms, messages et tests en **français**.
- Pas de dépendance ajoutée sans en parler : chaque dépendance s'installe dans tous les dépôts de parcours.
- Chaque étape livre une preuve testable (voir le plan) ; les tests passent avant de pousser.
- Paquets reproductibles : même contenu → même archive (dates et ordre des fichiers ZIP fixés).
- Les clés d'étapes publiées ne changent jamais (`cles.lock`, à partir de M2).

## Statuts et clés publiées (M2)

- `E(…, statut="brouillon" | "verifie" | "publie")`, brouillon par défaut, donné par son nom. Seul le cours des
  étapes publiées sort ; les autres affichent leur fiche. Vérifié ou publié sans cours : refusé.
- `Etape.publiee` décide de ce qui sort ; `Etape.redigee` veut dire « cours écrit ». `site.montre_cours(e)` :
  publiée, ou rédigée dans l'aperçu (`--brouillons`, bandeau réutilisant `.a-venir` : style commun inchangé).
- `cles.lock` (texte, une clé par ligne, triées, fins de ligne Unix) : la construction refuse une clé absente du
  registre, une étape publiée absente de la liste, des publiées sans fichier, une clé hors du format plateforme.
  Seul `moteur verifier --maj-cles` l'écrit (ajoute seulement). Dépublier est permis.
- `moteur construire` rend les pages en mémoire, lance `verifier.controler`, lève la première erreur avant
  d'écrire quoi que ce soit.

## État (au 27/11/2026, fin de M2)

- [x] **M0** : squelette (pyproject, commande `moteur` avec `--version` et l'aide, sous-commandes qui annoncent
      leur étape, tests, CI, README, licence MIT). Version `0.0.1`, pas encore d'étiquette.
- [x] **M1** (v0.1.0) : registre, blocs objets, sortie site, modèle commun, `moteur construire` et `moteur comparer`.
      Complexité construit avec le moteur ; site identique à l'ancien `build.py` (43 fichiers, 25 296 175 octets),
      vérifié par `moteur comparer` et `diff -r`. 102 tests (Linux et Windows).
- [x] **M2** (v0.2.0, `ea5fd39`) : statuts, sortie site des seules étapes publiées, aperçu `--brouillons`,
      `cles.lock`, `moteur verifier` (+ `--maj-cles`). Preuve : `test_renommer_une_cle_publiee_fait_echouer_la_construction`
      (158 tests, Linux et Windows) ; Complexité épinglé à v0.2.0 avec ses 3 étapes publiées : site identique à celui de
      v0.1.1 (PR parcours-complexite#3, actions vertes ; à fusionner après #2).
- [ ] M3 : sortie paquet au format 1, contrôlée par `lire_paquet`, importée dans la plateforme locale.
- [ ] M4 : composants partagés + évaluations en données (format suivant, défini d'abord dans la plateforme).
- [ ] M5 : PDF LaTeX.
- [ ] M6 : vidéos Bunny + action GitHub qui envoie le paquet à l'API d'import.

## À reprendre plus tard (repéré pendant M1)

- `modele/site.js` dit « Commencer ce module » : à rendre réglable quand un parcours aura des chapitres.
- `outils.js` mêle le thème (commun) et la progression de l'accueil : à séparer avec l'accueil générique
  (migration de Terminale). `animateur.js` (moteur + algorithmes) reste dans Complexité jusqu'à M4.
- L'archive hors ligne jointe à chaque version (décision de publication) n'est pas encore faite :
  à ajouter quand un parcours aura sa première étiquette.
- La construction ne vide pas le dossier de sortie (comme l'ancien build.py) ; en CI il part vide.
- `moteur verifier` ne contrôle pas les liens des brouillons, ni les liens vers des fichiers (vidéos, images).

## Journal

- 26/11/2026 — M0 : squelette créé, 10 tests passent sur Python 3.11 et 3.13, installation pip vérifiée dans un environnement neuf.
- 26/11/2026 — M1 : plan en QCM (blocs objets + Suite stricte ; moteur = socle + atelier/mesure, Complexité garde
  son CSS, animateur, calculateurs et pages propres ; preuve par `moteur comparer` ; publication par action en fin
  de M1). Registre, blocs, réglages, chargement, sortie site, modèle et comparateur livrés ; tests de rendu contre
  les anciennes briques. Complexité migré (PR AlsenyTECH/parcours-complexite#1) : sites identiques. Version 0.1.0 ;
  étiquette à poser par Alseny.
- 26/11/2026 — v0.1.0 étiquetée par Alseny. CI élargie à Windows : trois défauts corrigés (message d'erreur avec
  « \ », test de fin de ligne écrit en mode texte, cache de filecmp qui masquait un fichier réécrit dans la même
  seconde → lecture octet par octet). Version 0.1.1 sur main, étiquette à poser ; Complexité reste sur v0.1.0
  jusqu'à M2 (la montée de version se prouvera avec moteur comparer).
- 27/11/2026 — v0.1.1 étiquetée par Alseny. PR Complexité #1 fusionnée ; site publié par l'action, construit avec le moteur
  v0.1.0. **M1 terminé.** Prochaine tâche : M2 (statuts, `cles.lock`, `moteur verifier`), avec le passage de Complexité
  à v0.1.1 prouvé par `moteur comparer`.
- 27/11/2026 — M2 : plan en QCM (statuts dans le registre ; cles.lock en texte, écrit par `moteur verifier --maj-cles`,
  la construction lit et refuse ; verifier = socle complet avec avertissements ; aperçu `--brouillons` dans
  `_apercu/`). Complexité passé à v0.1.1 (PR parcours-complexite#2, sites identiques). E1 statuts, E2 sortie site
  et aperçu, E3 `cles.lock` (preuve : renommer une clé publiée fait échouer la construction), E4 `moteur verifier`,
  CI qui lance verifier sur l'exemple. Version 0.2.0 ; étiquette à poser par Alseny ; puis E5 dans Complexité.
- 27/11/2026 — PR #1 fusionnée, v0.2.0 étiquetée par Alseny (une première étiquette posée avant la fusion visait
  l'ancien main : supprimée et reposée sur `ea5fd39`). Retenir : **fusionner d'abord, étiqueter ensuite**, et vérifier
  `git --no-pager log -1 --oneline vX.Y.Z`. Complexité : PR #3 (v0.2.0, 3 étapes publiées, cles.lock), sites identiques.
  **M2 terminé.** Prochaine tâche : M3 (sortie paquet au format 1, contrôlée par `lire_paquet`).
