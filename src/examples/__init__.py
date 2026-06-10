"""Wbudowane przyklady scenariuszy DS1.

Kazdy przyklad to osobny modul z funkcja run(). Importy ponizej
zachowuja stare nazwy run_exampleN dla zgodnosci z CLI.
"""

from src.examples.projektor import run as run_example1
from src.examples.serwerownia import run as run_example2
from src.examples.bledny import run as run_example3
from src.examples.smoke_wraca import run as run_example4
from src.examples.precondition_z5 import run as run_example5

__all__ = [
    "run_example1",
    "run_example2",
    "run_example3",
    "run_example4",
    "run_example5",
]
