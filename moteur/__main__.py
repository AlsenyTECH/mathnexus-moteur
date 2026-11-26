"""Permet aussi `python -m moteur …`, utile quand la commande `moteur` n'est pas dans le PATH."""
import sys

from .cli import principal

sys.exit(principal())
