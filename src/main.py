from src.parser import parse_domain, parse_scenario, parse_query
from src.solver import solve
from src.query_engine import execute_query
from src.validator import validate


def main():
    print("=" * 60)
    print("  SCENARIUSZE DZIALAŃ — System DS1")
    print("=" * 60)

    # --- Wczytaj dziedzine ---
    print("\nPodaj opis dziedziny (pusta linia konczy):")
    domain_lines = []
    while True:
        line = input()
        if line.strip() == '':
            break
        domain_lines.append(line)
    domain_text = '\n'.join(domain_lines)
    domain = parse_domain(domain_text)
    print(f"  Wczytano dziedzine: {len(domain.durations)} akcji, "
          f"{len(domain.causes)} skutkow, {len(domain.releases)} releases, "
          f"{len(domain.triggers)} triggers, {len(domain.state_triggers)} wyzwalaczy stanowych")

    # --- Wczytaj scenariusz ---
    print("\nPodaj scenariusz (OBS/ACS, pusta linia konczy):")
    scenario_lines = []
    while True:
        line = input()
        if line.strip() == '':
            break
        scenario_lines.append(line)
    scenario_text = '\n'.join(scenario_lines)
    scenario = parse_scenario(scenario_text)
    print(f"  Wczytano scenariusz: {len(scenario.observations)} obserwacji, "
          f"{len(scenario.action_declarations)} deklaracji akcji")

    # --- Walidacja ---
    errors = validate(domain, scenario)
    if errors:
        print("\nBledy walidacji scenariusza:")
        for e in errors:
            print(f"  {e}")
        print("\nScenariusz narusza zalozenia DS1. Przerywam.")
        return

    # --- Rozwiaz ---
    models = _solve_and_print(domain, scenario)

    # --- Kwerendy ---
    print("\nPodaj kwerendy (pusta linia konczy):")
    while True:
        line = input("  > ")
        if line.strip() == '':
            break
        try:
            query = parse_query(line.strip())
            result = execute_query(query, models)
            print(f"  => {result}")
        except Exception as e:
            print(f"  Blad: {e}")


def run_from_file(filepath):
    """
    Wczytuje dziedzine, scenariusz i kwerendy z pliku tekstowego.

    Format pliku:
        DOMAIN:
        <instrukcje dziedziny, po jednej w linii>

        SCENARIO:
        OBS:
        (formula, czas)
        ACS:
        (akcja, czas)

        QUERIES:
        <kwerendy, po jednej w linii>

    Komentarze (#) i puste linie sa ignorowane.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    print("=" * 60)
    print(f"  Wczytywanie z pliku: {filepath}")
    print("=" * 60)

    # Podziel na sekcje
    domain_text, scenario_text, queries_text = _parse_file_sections(content)

    # --- Dziedzina ---
    domain = parse_domain(domain_text)
    print(f"\n  Dziedzina: {len(domain.durations)} akcji, "
          f"{len(domain.causes)} skutkow, {len(domain.releases)} releases, "
          f"{len(domain.triggers)} triggers, {len(domain.state_triggers)} wyzwalaczy stanowych")

    # --- Scenariusz ---
    scenario = parse_scenario(scenario_text)
    print(f"  Scenariusz: {len(scenario.observations)} obserwacji, "
          f"{len(scenario.action_declarations)} deklaracji akcji")

    # --- Walidacja ---
    if not _print_validation(domain, scenario):
        return

    # --- Rozwiaz ---
    models = _solve_and_print(domain, scenario)

    # --- Kwerendy ---
    if queries_text.strip():
        print("\nKwerendy:")
        for line in queries_text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                query = parse_query(line)
                result = execute_query(query, models)
                print(f"  {line} => {result}")
            except Exception as e:
                print(f"  {line} => Blad: {e}")


def _parse_file_sections(content):
    """Dzieli plik na sekcje DOMAIN, SCENARIO, QUERIES."""
    domain_lines = []
    scenario_lines = []
    queries_lines = []
    current = None

    for line in content.split('\n'):
        stripped = line.strip().upper()
        if stripped.startswith('DOMAIN'):
            current = 'domain'
            continue
        elif stripped.startswith('SCENARIO'):
            current = 'scenario'
            continue
        elif stripped.startswith('QUERIES') or stripped.startswith('QUERY'):
            current = 'queries'
            continue

        if current == 'domain':
            domain_lines.append(line)
        elif current == 'scenario':
            scenario_lines.append(line)
        elif current == 'queries':
            queries_lines.append(line)

    return '\n'.join(domain_lines), '\n'.join(scenario_lines), '\n'.join(queries_lines)


def _solve_and_print(domain, scenario):
    """Generuje modele i wypisuje wyniki. Zwraca liste modeli."""
    print("\nGenerowanie modeli...")
    models = solve(domain, scenario)
    print(f"  Znaleziono {len(models)} model(i)")

    if models:
        for i, m in enumerate(models):
            print(f"\n  Model {i + 1}:")
            print(f"    Akcje: {[(ex.action, ex.start_time, ex.end_time) for ex in m.executions]}")
            max_t = max(t for (_, t) in m.history.keys()) if m.history else 0
            fluents = sorted(set(f for (f, _) in m.history.keys()))
            for f in fluents:
                vals = [m.history.get((f, t), '?') for t in range(max_t + 1)]
                occ = ['*' if (f, t) in m.occlusion else '' for t in range(max_t + 1)]
                print(f"    {f}: {['T' + o if v else 'F' + o if v is not None else '?' for v, o in zip(vals, occ)]}")

    return models


def _print_validation(domain, scenario):
    """Wyswietla wyniki walidacji. Zwraca True jesli OK."""
    errors = validate(domain, scenario)
    if errors:
        print("\nBledy walidacji scenariusza:")
        for e in errors:
            print(f"  {e}")
        return False
    print("\nWalidacja: OK")
    return True


def run_example1():
    """Uruchamia Przyklad 1 (projektor) automatycznie."""
    print("=" * 60)
    print("  PRZYKLAD 1: Projektor")
    print("=" * 60)

    domain = parse_domain("""
press_power duration 1
press_power releases projector_on during [0,1]
impossible press_power if projector_on
""")

    scenario = parse_scenario("""
OBS:
(~projector_on, 0)
ACS:
(press_power, 0)
""")

    if not _print_validation(domain, scenario):
        return

    models = _solve_and_print(domain, scenario)

    queries = [
        "possibly Sc",
        "necessary performing press_power at 1 when Sc",
        "necessary projector_on at 2 when Sc",
        "possibly projector_on at 2 when Sc",
    ]
    print("\nKwerendy:")
    for q_text in queries:
        query = parse_query(q_text)
        result = execute_query(query, models)
        print(f"  {q_text} => {result}")


def run_example2():
    """Uruchamia Przyklad 2 (serwerownia) automatycznie."""
    print("\n" + "=" * 60)
    print("  PRZYKLAD 2: Serwerownia")
    print("=" * 60)

    domain = parse_domain("""
activate_alarm duration 1
activate_alarm causes alarm_on after 1 if smoke
smoke causes activate_alarm
impossible activate_alarm if maintenance
activate_alarm triggers start_ventilation after 1
start_ventilation duration 2
start_ventilation releases ventilation_on during [0,2]
start_ventilation causes ventilation_on after 2 if alarm_on
""")

    scenario = parse_scenario("""
OBS:
(smoke & ~maintenance & ~alarm_on & ~ventilation_on, 0)
ACS:
""")

    if not _print_validation(domain, scenario):
        return

    models = _solve_and_print(domain, scenario)

    queries = [
        "possibly Sc",
        "necessary performing activate_alarm at 0 when Sc",
        "necessary alarm_on at 1 when Sc",
        "necessary performing start_ventilation at 2 when Sc",
        "necessary ventilation_on at 4 when Sc",
    ]
    print("\nKwerendy:")
    for q_text in queries:
        query = parse_query(q_text)
        result = execute_query(query, models)
        print(f"  {q_text} => {result}")


def run_example3():
    """Przyklad 3 — celowo bledny scenariusz (walidacja powinna go odrzucic)."""
    print("\n" + "=" * 60)
    print("  PRZYKLAD 3: Bledny scenariusz (test walidacji)")
    print("=" * 60)

    domain = parse_domain("""
repair duration 3
reboot duration 2
reboot causes system_on after 2 if ~broken
impossible reboot at 0
""")

    scenario = parse_scenario("""
OBS:
(broken, 0)
(~broken, 0)
ACS:
(repair, 0)
(reboot, 1)
(reboot, 0)
""")

    print("\nDziedzina:")
    print("  repair duration 3")
    print("  reboot duration 2")
    print("  reboot causes system_on after 2 if ~broken")
    print("  impossible reboot at 0")
    print("\nScenariusz:")
    print("  OBS: (broken, 0) oraz (~broken, 0)")
    print("  ACS: (repair, 0), (reboot, 1), (reboot, 0)")

    errors = validate(domain, scenario)
    if errors:
        print(f"\nWalidacja wykryla {len(errors)} bledow:")
        for e in errors:
            print(f"  {e}")
        print("\nScenariusz odrzucony — nie spelnia zalozen DS1.")
    else:
        print("\nWalidacja: OK")
        models = solve(domain, scenario)
        print(f"Znaleziono {len(models)} model(i)")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--example1':
        run_example1()
    elif len(sys.argv) > 1 and sys.argv[1] == '--example2':
        run_example2()
    elif len(sys.argv) > 1 and sys.argv[1] == '--example3':
        run_example3()
    elif len(sys.argv) > 1 and sys.argv[1] == '--examples':
        run_example1()
        run_example2()
        run_example3()
    elif len(sys.argv) > 1:
        run_from_file(sys.argv[1])
    else:
        main()
