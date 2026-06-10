"""Przyklad 5 — Z5: warunek poczatkowy blokuje start akcji.

Regula 'reboot causes system_on after 2 if ~broken' implikuje warunek
poczatkowy ~broken w start_time. Jesli scenariusz deklaruje reboot gdy
broken=True, akcja w ogole sie nie wykonuje -> 0 modeli (nierealizowalny).
"""

from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    CausesStatement, DurationStatement,
    AtomicFormula, Negation,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.examples.helpers import (
    query_times, solve_and_print, print_validation, print_queries,
    print_domain, print_scenario,
)


def run():
    print("\n" + "=" * 60)
    print("  PRZYKLAD 5: Z5 — precondition blokuje start akcji")
    print("=" * 60)
    print("""
Co pokazuje:
  Zalozenie Z5: 'a causes alpha after delta if pi' implikuje, ze pi
  jest warunkiem poczatkowym akcji a — akcja moze sie rozpoczac TYLKO
  gdy pi zachodzi w start_time.

  Dziedzina: reboot wymaga zeby system NIE byl broken (precondition ~broken)
  Scenariusz: system zepsuty (broken=True w t=0), user proboje od razu
  zrobic reboot w t=0 -> precondition naruszona -> 0 modeli.

  Walidator nie odrzuca tego scenariusza (brak naruszen sekwencyjnosci ani
  impossible_at). To solver wykrywa nierealizowalnosc dzieki Z5.
""")

    # Dziedzina:
    #   reboot duration 2
    #   reboot causes system_on after 2 if ~broken
    #   repair duration 3
    #   repair causes ~broken after 3
    domain = Domain(
        durations=[
            DurationStatement("reboot", 2),
            DurationStatement("repair", 3),
        ],
        causes=[
            CausesStatement(
                "reboot",
                AtomicFormula("system_on"),
                2,
                Negation(AtomicFormula("broken")),
            ),
            CausesStatement(
                "repair",
                Negation(AtomicFormula("broken")),
                3,
                None,
            ),
        ],
    )

    # Scenariusz:
    #   OBS: (broken, 0)
    #   ACS: (reboot, 0)        <- precondition ~broken nie spelniony!
    scenario = Scenario(
        observations=[Observation(AtomicFormula("broken"), 0)],
        action_declarations=[ActionDeclaration("reboot", 0)],
    )

    # Uzywamy 'possibly' bo na pustym zbiorze modeli 'necessary' zwraca
    # True (vacuous truth — "dla kazdego z 0 modeli" trywialnie True),
    # co bylo by mylace dla scenariusza nierealizowalnego.
    queries = [
        ("possibly Sc",
         QueryPossiblyScenario()),
        ("possibly performing reboot at 0 when Sc",
         QueryPerforming("possibly", "reboot", 0)),
        ("possibly system_on at 2 when Sc",
         QueryCondition("possibly", AtomicFormula("system_on"), 2)),
    ]

    print_domain(domain)
    print_scenario(scenario)

    if not print_validation(domain, scenario):
        return

    models = solve_and_print(domain, scenario, extra_times=query_times(queries))
    print_queries(queries, models)

    if not models:
        print("\n  >>> Scenariusz nierealizowalny: precondition ~broken nie zachodzi")
        print("  >>> w start_time akcji reboot (broken=True w t=0).")
