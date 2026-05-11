from src.parser import parse_domain, parse_scenario, parse_query
from src.solver import solve
from src.query_engine import execute_query


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

    # --- Rozwiaz ---
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

    models = solve(domain, scenario)
    print(f"\nZnaleziono {len(models)} model(i)")
    for i, m in enumerate(models):
        print(f"\n  Model {i + 1}:")
        print(f"    Akcje: {[(ex.action, ex.start_time, ex.end_time) for ex in m.executions]}")
        max_t = max(t for (_, t) in m.history.keys()) if m.history else 0
        fluents = sorted(set(f for (f, _) in m.history.keys()))
        for f in fluents:
            vals = ['T' if m.history.get((f, t)) else 'F' for t in range(max_t + 1)]
            print(f"    {f}: {vals}")

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

    models = solve(domain, scenario)
    print(f"\nZnaleziono {len(models)} model(i)")
    for i, m in enumerate(models):
        print(f"\n  Model {i + 1}:")
        print(f"    Akcje: {[(ex.action, ex.start_time, ex.end_time) for ex in m.executions]}")
        max_t = max(t for (_, t) in m.history.keys()) if m.history else 0
        fluents = sorted(set(f for (f, _) in m.history.keys()))
        for f in fluents:
            vals = ['T' if m.history.get((f, t)) else 'F' for t in range(max_t + 1)]
            print(f"    {f}: {vals}")

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


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--example1':
        run_example1()
    elif len(sys.argv) > 1 and sys.argv[1] == '--example2':
        run_example2()
    elif len(sys.argv) > 1 and sys.argv[1] == '--examples':
        run_example1()
        run_example2()
    else:
        main()
