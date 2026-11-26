"""Les briques d'écriture du cours. Chacune renvoie un **objet**, plus une chaîne HTML.

On écrit toujours le cours de la même façon, avec les mêmes signatures :

    from moteur.blocs import retenir, video, exercice

    COMPRENDRE = r\"\"\"<p class="lead">…</p>\"\"\" + video("m3-insertion.mp4", "Le tri", "7 min 41") + r\"\"\"
    <p>…</p>\"\"\"

Mais `video(…)` renvoie un objet `Video(fichier, legende, duree)`, et `"…" + video(…) + "…"`
renvoie une `Suite` : la liste des morceaux, HTML simple ou blocs. Le cours garde donc sa
structure, et chaque sortie la rend à sa façon : le site (moteur.sorties.site), le paquet de la
plateforme (M3), le LaTeX des PDF (M5).

Règle stricte : un bloc n'est pas une chaîne. L'insérer dans `"%s" % bloc`, `f"{bloc}"` ou
`"".join([…])` lève une erreur, car la structure y serait perdue sans prévenir. On assemble avec `+`,
ou avec `assembler(…)` pour une liste.

Le HTML simple (p, strong, ul, table, pre…) et le TeX entre \\( \\) et \\[ \\] restent des chaînes.
"""
import dataclasses
from dataclasses import dataclass, field


def donnee(**options):
    """Un champ de données (identifiant, code source, réglage d'un outil) : ce n'est pas du texte de
    cours, `enfants` et `parcourir` l'ignorent."""
    return field(metadata={"cours": False}, **options)


class Bloc:
    """Ce que toutes les briques ont en commun : on les assemble avec `+`."""

    def __add__(self, autre):
        return assembler(self, autre)

    def __radd__(self, autre):
        return assembler(autre, self)

    def __str__(self):
        raise TypeError(
            "%s est un bloc, pas une chaîne : assemble-le avec + (ou assembler(…)), "
            "pas avec %%, format, f-string ou join." % type(self).__name__)


def _verifier_morceau(m):
    if not isinstance(m, (str, Bloc)):
        raise TypeError("un morceau de cours doit être du texte (HTML) ou un bloc, pas %s : %r"
                        % (type(m).__name__, m))


@dataclass(frozen=True)
class Suite(Bloc):
    """Des morceaux à la suite : chaînes HTML et blocs, dans l'ordre."""
    morceaux: tuple

    def __post_init__(self):
        for m in self.morceaux:
            _verifier_morceau(m)


def assembler(*morceaux):
    """Met des morceaux à la suite. Les Suites imbriquées sont aplaties, les chaînes vides retirées.

    assembler("<p>a</p>", video(…), "<p>b</p>")  ==  "<p>a</p>" + video(…) + "<p>b</p>"
    """
    plats = []
    for m in morceaux:
        _verifier_morceau(m)
        if isinstance(m, Suite):
            plats.extend(m.morceaux)
        elif m != "":
            plats.append(m)
    return Suite(tuple(plats))


def enfants(noeud):
    """Les morceaux de cours directement contenus dans un bloc (texte, blocs, listes de textes)."""
    if isinstance(noeud, Suite):
        return list(noeud.morceaux)
    trouves = []
    for f in dataclasses.fields(noeud):
        if not f.metadata.get("cours", True):
            continue
        trouves.extend(_aplatir(getattr(noeud, f.name)))
    return trouves


def _aplatir(valeur):
    if isinstance(valeur, (str, Bloc)):
        return [valeur]
    if isinstance(valeur, (tuple, list)):
        return [x for v in valeur for x in _aplatir(v)]
    return []


def parcourir(noeud):
    """Le nœud, puis tous les blocs et textes qu'il contient, en profondeur (ordre du document)."""
    yield noeud
    if isinstance(noeud, Bloc):
        for e in enfants(noeud):
            yield from parcourir(e)


def _tuple(valeur):
    """Les listes deviennent des tuples : un bloc ne change plus une fois créé."""
    if isinstance(valeur, list):
        return tuple(_tuple(v) for v in valeur)
    if isinstance(valeur, tuple):
        return tuple(_tuple(v) for v in valeur)
    return valeur


# ─────────────────────────────────────────────────────────────────────────────
# Encadrés
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Retenir(Bloc):
    label: object
    corps: object


@dataclass(frozen=True)
class Demo(Bloc):
    corps: object
    label: object = "Démonstration"


@dataclass(frozen=True)
class Prof(Bloc):
    corps: object
    label: object = "Le conseil"


@dataclass(frozen=True)
class Master(Bloc):
    corps: object
    label: object = "En cryptographie"


@dataclass(frozen=True)
class Examen(Bloc):
    """Ce qui tombe à l'examen, et comment le rédiger."""
    corps: object
    label: object = "À l'examen"


@dataclass(frozen=True)
class Methode(Bloc):
    """Une méthode numérotée, à appliquer telle quelle."""
    titre: object
    etapes: tuple


@dataclass(frozen=True)
class ARetenir(Bloc):
    lignes: tuple


@dataclass(frozen=True)
class AToi(Bloc):
    enonce: object
    solution: object


def retenir(label, corps):
    return Retenir(label, corps)


def demo(corps, label="Démonstration"):
    return Demo(corps, label)


def prof(corps, label="Le conseil"):
    return Prof(corps, label)


def master(corps, label="En cryptographie"):
    return Master(corps, label)


def examen(corps, label="À l'examen"):
    return Examen(corps, label)


def methode(titre, etapes_):
    return Methode(titre, _tuple(etapes_))


def a_retenir(lignes):
    return ARetenir(_tuple(lignes))


def a_toi(enonce, solution):
    return AToi(enonce, solution)


# ─────────────────────────────────────────────────────────────────────────────
# Démonstrations, exercices, tests
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Preuve(Bloc):
    """Un théorème à démontrer soi-même : l'énoncé, l'idée, le squelette, puis la preuve repliée."""
    enonce_label: object
    enonce: object
    idee: object
    etapes: tuple
    complete: object


@dataclass(frozen=True)
class Exercice(Bloc):
    """Exercice gradué : énoncé, indice replié, correction repliée."""
    n: object
    niveau: object
    enonce: object
    indice: object
    correction: object
    remarque: object = None


@dataclass(frozen=True)
class Exo(Bloc):
    """Exercice simple : énoncé et correction repliée, sans indice."""
    n: object
    enonce: object
    correction: object
    remarque: object = None
    niveau: object = None


@dataclass(frozen=True)
class Question(Bloc):
    """Une question de QCM. `bonne` est l'indice (à partir de 0) de la bonne option."""
    enonce: object
    options: tuple
    bonne: int = donnee()
    explication: object = None


ROLES_QCM = ("entree", "sortie")


@dataclass(frozen=True)
class Qcm(Bloc):
    """Test à choix, corrigé dans le navigateur.

    role  "entree" (permet de sauter l'étape) ou "sortie" (valide l'étape)
    """
    role: str = donnee()
    questions: tuple = ()

    def __post_init__(self):
        if self.role not in ROLES_QCM:
            raise ValueError("qcm : rôle %r inconnu (attendu : %s)" % (self.role, ", ".join(ROLES_QCM)))
        if not self.questions:
            raise ValueError("qcm : au moins une question")

    @property
    def seuil(self):
        """Bonnes réponses exigées : toutes pour sauter l'étape, une erreur permise pour la valider."""
        n = len(self.questions)
        return n if self.role == "entree" else max(1, n - 1)


def preuve(enonce_label, enonce, idee, etapes, complete):
    return Preuve(enonce_label, enonce, idee, _tuple(etapes), complete)


def exercice(n, niveau, enonce, indice, correction, remarque=None):
    return Exercice(n, niveau, enonce, indice, correction, remarque)


def exo(n, enonce, correction, remarque=None, niveau=None):
    return Exo(n, enonce, correction, remarque, niveau)


def qcm(role, questions):
    """questions : liste de (énoncé, [options], indice de la bonne option, explication)."""
    qs = []
    for i, q in enumerate(questions):
        if isinstance(q, Question):
            qs.append(q)
            continue
        enonce, options, bonne, explication = q
        if not 0 <= bonne < len(options):
            raise ValueError("qcm : question %d, la bonne option %d n'existe pas (%d options)"
                             % (i + 1, bonne, len(options)))
        qs.append(Question(enonce, _tuple(options), bonne, explication))
    return Qcm(role, tuple(qs))


# ─────────────────────────────────────────────────────────────────────────────
# L'étape en quatre temps
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class QuatreTemps(Bloc):
    """Une étape au gabarit : test d'entrée, quatre temps en onglets, test de sortie, à retenir.

    Les noms des temps (Comprendre, Démontrer, Implémenter, S'exercer) viennent des réglages du
    parcours : le troisième change selon la discipline.
    """
    entree: object
    comprendre: object
    demontrer: object
    implementer: object
    exercer: object
    sortie: object
    retenir: object


def etape(entree, comprendre, demontrer, implementer, exercer, sortie, retenir_):
    return QuatreTemps(entree, comprendre, demontrer, implementer, exercer, sortie, retenir_)


# ─────────────────────────────────────────────────────────────────────────────
# Code, tableaux, vidéos
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Code(Bloc):
    """Un programme affiché (pas exécuté). `src` et `sortie` sont du texte brut, échappé au rendu."""
    src: str = donnee()
    lang: str = donnee(default="python")
    sortie: str = donnee(default=None)
    titre: object = "Implémentation"


@dataclass(frozen=True)
class Tableau(Bloc):
    entetes: tuple
    lignes: tuple
    classe: str = donnee(default="")


@dataclass(frozen=True)
class Video(Bloc):
    """Une vidéo du parcours. Les sous-titres <nom>.vtt sont joints au rendu s'ils existent."""
    fichier: str = donnee()
    legende: object = None
    duree: str = donnee(default="")


@dataclass(frozen=True)
class VideoAttente(Bloc):
    sujet: object


def code(src, lang="python", sortie=None, titre="Implémentation"):
    return Code(src, lang, sortie, titre)


def tableau(entetes, lignes, classe=""):
    return Tableau(_tuple(entetes), _tuple(lignes), classe)


def video(fichier, legende, duree):
    return Video(fichier, legende, duree)


def video_attente(sujet):
    return VideoAttente(sujet)


# ─────────────────────────────────────────────────────────────────────────────
# Outils interactifs : atelier de code, SageMath, animateur, mesure
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Atelier(Bloc):
    """Atelier de code : l'étudiant complète `depart`, puis lance des tests cachés dans son navigateur.

    tests  dictionnaires {"appel", "verif", "attendu"} ou {"appel", "leve", "attendu"} ;
           `verif` est une expression Python qui teste la propriété attendue du résultat r.
    """
    ident: str = donnee()
    consigne: object = None
    depart: str = donnee(default="")
    tests: tuple = donnee(default=())
    corrige: object = None


@dataclass(frozen=True)
class SageAtelier(Bloc):
    """Cellule SageMath modifiable (service SageMathCell)."""
    consigne: object
    depart: str = donnee(default="")


@dataclass(frozen=True)
class Animateur(Bloc):
    """Animateur pas à pas d'un algorithme connu du composant JavaScript (ex. "insertion").

    entrees  (nom, tableau) proposés à l'étudiant
    """
    ident: str = donnee()
    algo: str = donnee(default="")
    entrees: tuple = donnee(default=())
    legende: object = None


@dataclass(frozen=True)
class Mesure(Bloc):
    """Mesure expérimentale du coût d'une fonction de l'atelier `ident` (voir la docstring de mesure)."""
    ident: str = donnee()
    consigne: object = None
    fonction: str = donnee(default="")
    tailles: tuple = donnee(default=())
    courbes: tuple = donnee(default=())
    cas: tuple = donnee(default=())
    ratios: tuple = donnee(default=())
    axe: str = donnee(default="taille n du tableau")


def atelier(ident, consigne, depart, tests, corrige):
    return Atelier(ident, consigne, depart, _tuple(tests), corrige)


def sage_atelier(consigne, depart):
    return SageAtelier(consigne, depart)


def animateur(ident, algo, entrees, legende):
    return Animateur(ident, algo, _tuple(entrees), legende)


def mesure(ident, consigne, fonction, tailles, courbes, cas, ratios=(), axe="taille n du tableau"):
    """La fonction `fonction` de l'atelier `ident` est lancée sur des entrées de tailles croissantes ;
    le compteur qu'elle renvoie (2e élément du couple) est tracé.

    tailles  liste de n
    courbes  liste de (nom, expression JavaScript en n), tracées en pointillés
    cas      liste de dicts {"nom", "court", "expr", "couleur", "essais"} : expr est une expression
             Python en n qui renvoie le TUPLE des arguments ; couleur ∈ meilleur | moyen | pire | autre ;
             "fonction" (facultatif) : une autre fonction de l'atelier pour ce cas
    ratios   liste de (titre de colonne, indice du cas, expression JavaScript en n)
    """
    return Mesure(ident, consigne, fonction, _tuple(tailles), _tuple(courbes), _tuple(cas),
                  _tuple(ratios), axe)
