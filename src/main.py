from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    CausesStatement, DurationStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement,
    ImpossibleIfStatement, ImpossibleAtStatement,
    AtomicFormula, Negation, Conjunction,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.solver import solve
from src.query_engine import execute_query
from src.validator import validate


# ========================= POMOCNICZE =========================

def _query_times(queries):
    """Wyciaga czasy wystepujace w kwerendach (do horyzontu)."""
    times = []
    for _, q in queries:
        if isinstance(q, (QueryPerforming, QueryCondition)):
            times.append(q.time)
    return times


def _solve_and_print(domain, scenario, extra_times=()):
    """Generuje modele i wypisuje wyniki. Zwraca liste modeli."""
    print("\nGenerowanie modeli...")
    models = solve(domain, scenario, extra_times=extra_times)
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


def _print_queries(queries, models):
    """Uruchamia liste (etykieta, obiekt_kwerendy) i wypisuje wyniki."""
    print("\nKwerendy:")
    for label, query in queries:
        result = execute_query(query, models)
        print(f"  {label} => {result}")


# ========================= PRZYKLADY =========================

def run_example1():
    """Przyklad 1 — Projektor."""
    print("=" * 60)
    print("  PRZYKLAD 1: Projektor")
    print("=" * 60)

    # Dziedzina:
    domain = Domain(
        durations=[DurationStatement("press_power", 1)],
        releases=[ReleasesStatement("press_power", "projector_on", 0, 1)],
        impossible_if=[ImpossibleIfStatement("press_power", AtomicFormula("projector_on"))],
    )

    # Scenariusz:
    scenario = Scenario(
        observations=[Observation(Negation(AtomicFormula("projector_on")), 0)],
        action_declarations=[ActionDeclaration("press_power", 0)],
    )

    queries = [
        ("possibly Sc",
         QueryPossiblyScenario()),
        ("necessary performing press_power at 0 when Sc",
         QueryPerforming("necessary", "press_power", 0)),
        ("necessary performing press_power at 1 when Sc",
         QueryPerforming("necessary", "press_power", 1)),
        ("necessary projector_on at 2 when Sc",
         QueryCondition("necessary", AtomicFormula("projector_on"), 2)),
        ("possibly projector_on at 2 when Sc",
         QueryCondition("possibly", AtomicFormula("projector_on"), 2)),
    ]

    if not _print_validation(domain, scenario):
        return

    models = _solve_and_print(domain, scenario, extra_times=_query_times(queries))
    _print_queries(queries, models)


def run_example2():
    """Przyklad 2 — Serwerownia."""
    print("\n" + "=" * 60)
    print("  PRZYKLAD 2: Serwerownia")
    print("=" * 60)

    # Dziedzina:
    #   activate_alarm duration 1
    #   activate_alarm causes alarm_on after 1 if smoke
    #   smoke causes activate_alarm                 (wyzwalacz stanowy)
    #   impossible activate_alarm if maintenance
    #   activate_alarm triggers start_ventilation after 1
    #   start_ventilation duration 2
    #   start_ventilation releases ventilation_on during [0,2]
    #   start_ventilation causes ventilation_on after 2 if alarm_on
    domain = Domain(
        durations=[
            DurationStatement("activate_alarm", 1),
            DurationStatement("start_ventilation", 2),
        ],
        causes=[
            CausesStatement("activate_alarm", AtomicFormula("alarm_on"), 1,
                            AtomicFormula("smoke")),
            CausesStatement("start_ventilation", AtomicFormula("ventilation_on"), 2,
                            AtomicFormula("alarm_on")),
        ],
        releases=[
            ReleasesStatement("start_ventilation", "ventilation_on", 0, 2),
        ],
        triggers=[
            TriggersStatement("activate_alarm", "start_ventilation", 1),
        ],
        state_triggers=[
            StateTriggerStatement(AtomicFormula("smoke"), "activate_alarm"),
        ],
        impossible_if=[
            ImpossibleIfStatement("activate_alarm", AtomicFormula("maintenance")),
        ],
    )

    # Scenariusz:
    #   OBS: (smoke & ~maintenance & ~alarm_on & ~ventilation_on, 0)
    #   ACS: (puste)
    obs_formula = Conjunction(
        Conjunction(
            Conjunction(
                AtomicFormula("smoke"),
                Negation(AtomicFormula("maintenance")),
            ),
            Negation(AtomicFormula("alarm_on")),
        ),
        Negation(AtomicFormula("ventilation_on")),
    )
    scenario = Scenario(
        observations=[Observation(obs_formula, 0)],
        action_declarations=[],
    )

    queries = [
        ("possibly Sc",
         QueryPossiblyScenario()),
        ("necessary performing activate_alarm at 0 when Sc",
         QueryPerforming("necessary", "activate_alarm", 0)),
        ("necessary alarm_on at 1 when Sc",
         QueryCondition("necessary", AtomicFormula("alarm_on"), 1)),
        ("necessary performing start_ventilation at 2 when Sc",
         QueryPerforming("necessary", "start_ventilation", 2)),
        ("necessary ventilation_on at 4 when Sc",
         QueryCondition("necessary", AtomicFormula("ventilation_on"), 4)),
    ]

    if not _print_validation(domain, scenario):
        return

    models = _solve_and_print(domain, scenario, extra_times=_query_times(queries))
    _print_queries(queries, models)


def run_example3():
    """Przyklad 3 — celowo bledny scenariusz."""
    print("\n" + "=" * 60)
    print("  PRZYKLAD 3: Bledny scenariusz (test walidacji)")
    print("=" * 60)

    # Dziedzina:
    #   repair duration 3
    #   reboot duration 2
    #   reboot causes system_on after 2 if ~broken
    #   impossible reboot at 0
    domain = Domain(
        durations=[
            DurationStatement("repair", 3),
            DurationStatement("reboot", 2),
        ],
        causes=[
            CausesStatement(
                "reboot",
                AtomicFormula("system_on"),
                2,
                Negation(AtomicFormula("broken")),
            ),
        ],
        impossible_at=[ImpossibleAtStatement("reboot", 0)],
    )

    # Scenariusz (celowo bledny):
    #   OBS: (broken, 0), (~broken, 0)               <- sprzecznosc
    #   ACS: (repair, 0), (reboot, 1), (reboot, 0)   <- nakladanie + impossible_at
    scenario = Scenario(
        observations=[
            Observation(AtomicFormula("broken"), 0),
            Observation(Negation(AtomicFormula("broken")), 0),
        ],
        action_declarations=[
            ActionDeclaration("repair", 0),
            ActionDeclaration("reboot", 1),
            ActionDeclaration("reboot", 0),
        ],
    )

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


# ========================= ENTRY POINT =========================

def _print_usage():
    print("Uzycie:")
    print("  python3 -m src.main --example1   # Projektor")
    print("  python3 -m src.main --example2   # Serwerownia")
    print("  python3 -m src.main --example3   # Bledny scenariusz (walidator)")
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
    elif arg == '--examples':
        run_example1()
        run_example2()
        run_example3()
    else:
        _print_usage()
        sys.exit(1)
