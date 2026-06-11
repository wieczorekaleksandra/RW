"""Punkt wejscia CLI. Ladowanie scenariuszy z plikow .txt + GUI."""

import os
import sys

from src.parser import parse_file, ParseError
from src.printers import (
    print_domain, print_scenario, print_validation,
    solve_and_print, print_queries, query_times,
)


# Sciezka do folderu z przykladami (relatywnie do tego pliku)
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
)

EXAMPLE_FILES = {
    1: "projektor.txt",
    2: "serwerownia.txt",
    3: "bledny.txt",
    4: "smoke_wraca.txt",
    5: "precondition_z5.txt",
}


def run_file(path):
    """Wczytaj plik .txt, wypisz wszystko i odpowiedz na kwerendy."""
    print("=" * 60)
    print(f"  {os.path.basename(path)}")
    print("=" * 60)

    try:
        domain, scenario, queries = parse_file(path)
    except FileNotFoundError:
        print(f"Nie znaleziono pliku: {path}", file=sys.stderr)
        sys.exit(1)
    except ParseError as e:
        print(f"Blad parsowania w '{path}':\n  {e}", file=sys.stderr)
        sys.exit(1)

    print_domain(domain)
    print_scenario(scenario)

    if not print_validation(domain, scenario):
        print("\nScenariusz odrzucony — nie spelnia zalozen DS1.")
        return

    models = solve_and_print(domain, scenario, extra_times=query_times(queries))
    if queries:
        print_queries(queries, models)


def run_example(n):
    """Uruchom wbudowany przyklad #n (laduje z examples/*.txt)."""
    filename = EXAMPLE_FILES.get(n)
    if filename is None:
        print(f"Nieznany przyklad: #{n}", file=sys.stderr)
        sys.exit(1)
    run_file(os.path.join(EXAMPLES_DIR, filename))


def _print_usage():
    print("Uzycie:")
    print("  python3 -m src.main --example1   # Projektor")
    print("  python3 -m src.main --example2   # Serwerownia")
    print("  python3 -m src.main --example3   # Bledny scenariusz (walidator)")
    print("  python3 -m src.main --example4   # Smoke wraca (edge-triggered)")
    print("  python3 -m src.main --example5   # Z5 precondition blokuje start")
    print("  python3 -m src.main --examples   # Wszystkie powyzsze")
    print("  python3 -m src.main --file PATH  # Wczytaj scenariusz z pliku .txt")
    print("  python3 -m src.main PATH         # (skrot) wczytaj plik .txt")
    print("  python3 -m src.main --gui        # Okienkowy interfejs (tkinter)")


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        _print_usage()
        sys.exit(0)

    arg = sys.argv[1]
    if arg in ('--example1', '--example2', '--example3', '--example4', '--example5'):
        run_example(int(arg[-1]))
    elif arg == '--examples':
        for n in range(1, 6):
            run_example(n)
    elif arg == '--file':
        if len(sys.argv) < 3:
            print("--file wymaga sciezki do pliku", file=sys.stderr)
            _print_usage()
            sys.exit(1)
        run_file(sys.argv[2])
    elif arg == '--gui':
        from src.gui import main as gui_main
        gui_main()
    elif arg.startswith('--'):
        _print_usage()
        sys.exit(1)
    else:
        # Skrot: pierwszym argumentem jest sciezka do pliku
        run_file(arg)
