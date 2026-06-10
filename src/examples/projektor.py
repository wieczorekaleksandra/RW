"""Przyklad 1 — Projektor.

Niedeterminizm z 'releases' (okluzja), 'impossible if', roznica
necessary vs possibly.
"""

from src.models import (
    Domain, Scenario, Observation, ActionDeclaration,
    DurationStatement, ReleasesStatement, ImpossibleIfStatement,
    AtomicFormula, Negation,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.examples.helpers import (
    query_times, solve_and_print, print_validation, print_queries,
    print_domain, print_scenario,
)


def run():
    print("=" * 60)
    print("  PRZYKLAD 1: Projektor")
    print("=" * 60)
    print("""
Co pokazuje:
  Niedeterminizm wynikajacy z 'releases' (okluzja fluentu w przedziale
  trwania akcji). Po wcisnieciu press_power projektor MOZE, ale nie musi
  sie wlaczyc — solver generuje 2 modele. Demonstruje tez 'impossible if'
  (nie mozna wcisnac jesli juz wlaczony) oraz roznice 'necessary' vs
  'possibly' w kwerendach.
""")

    domain = Domain(
        durations=[DurationStatement("press_power", 1)],
        releases=[ReleasesStatement("press_power", "projector_on", 0, 1)],
        impossible_if=[ImpossibleIfStatement("press_power", AtomicFormula("projector_on"))],
    )

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

    print_domain(domain)
    print_scenario(scenario)

    if not print_validation(domain, scenario):
        return

    models = solve_and_print(domain, scenario, extra_times=query_times(queries))
    print_queries(queries, models)
