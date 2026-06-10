"""Punkt wejscia CLI. Dispatch przykladow — implementacje w src/examples/."""

from src.examples import (
    run_example1,
    run_example2,
    run_example3,
    run_example4,
    run_example5,
)


def _print_usage():
    print("Uzycie:")
    print("  python3 -m src.main --example1   # Projektor")
    print("  python3 -m src.main --example2   # Serwerownia")
    print("  python3 -m src.main --example3   # Bledny scenariusz (walidator)")
    print("  python3 -m src.main --example4   # Smoke wraca (edge-triggered)")
    print("  python3 -m src.main --example5   # Z5 precondition blokuje start")
    print("  python3 -m src.main --examples   # Wszystkie powyzsze")


if __name__ == '__main__':
    import sys
    if len(sys.argv) <= 1:
        _print_usage()
        sys.exit(0)

    arg = sys.argv[1]
    if arg == '--example1':
        run_example1()
    elif arg == '--example2':
        run_example2()
    elif arg == '--example3':
        run_example3()
    elif arg == '--example4':
        run_example4()
    elif arg == '--example5':
        run_example5()
    elif arg == '--examples':
        run_example1()
        run_example2()
        run_example3()
        run_example4()
        run_example5()
    else:
        _print_usage()
        sys.exit(1)
