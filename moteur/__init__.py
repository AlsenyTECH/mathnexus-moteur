"""Moteur de contenu des parcours MathNexus.

Un seul format d'écriture (registre + briques), un seul générateur, trois sorties :
le site statique, le paquet pour la plateforme Mathnexus et les PDF.
"""

# Seule source du numéro de version : pyproject.toml la lit ici.
# Une version publiée correspond à une étiquette Git (v0.1.0 → 0.1.0), que les dépôts
# de parcours épinglent dans leurs dépendances.
__version__ = "0.3.0"
