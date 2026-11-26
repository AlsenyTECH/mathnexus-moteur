from moteur.registre import Etape as E, Partie

PARTIES = [
    Partie(1, "Premiers pas", "Le début du parcours.", [
        E("p1-depart", "Le départ", 20, "Savoir commencer."),
        E("p1-suite", "La suite", 25, "Savoir continuer.", ["p1-depart"], examen="Annale 2025, ex. 1",
          cours="Chapitre 1"),
    ]),
    Partie(2, "Aller plus loin", "La suite du parcours.", [
        E("p2-loin", "Plus loin", 30, "Savoir aller loin.", ["p1-suite"]),
    ]),
]
