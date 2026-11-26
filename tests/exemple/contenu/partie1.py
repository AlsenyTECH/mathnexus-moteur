from moteur.blocs import a_retenir, etape, exercice, qcm, retenir, video

from _commun import INTRO

CORPS = {}

CORPS["p1-depart"] = etape(
    qcm("entree", [("Combien ?", ["1", "2"], 1, "Deux.")]),
    INTRO + video("demo.mp4", "La démo", "1 min") + r"<p>Si \(a < b\) alors…</p>",
    retenir("Définition", "<p>Une définition.</p>"),
    "<p>Calcul.</p>",
    exercice(1, "★", "<p>Énoncé</p>", "<p>Indice</p>", "<p>Correction</p>"),
    qcm("sortie", [("Et donc ?", ["oui", "non"], 0, "Oui.")]),
    a_retenir(["Une chose."]),
)
