"""Przyklad 2 — Serwerownia.

Pelny zestaw mechanizmow DS1: wyzwalacz stanowy, dynamic trigger,
warunkowe efekty. Demo edge-triggered semantyki dla state triggera.
"""

from src.models import (
    Domain, Scenario, Observation,
    CausesStatement, DurationStatement, ReleasesStatement,
    TriggersStatement, StateTriggerStatement, ImpossibleIfStatement,
    AtomicFormula, Negation, Conjunction,
    QueryPossiblyScenario, QueryPerforming, QueryCondition,
)
from src.examples.helpers import (
    query_times, solve_and_print, print_validation, print_queries,
    print_domain, print_scenario,
)


def run():
    print("\n" + "=" * 60)
    print("  PRZYKLAD 2: Serwerownia")
    print("=" * 60)
    print("""
Co pokazuje:
  Pelny zestaw mechanizmow DS1 — wyzwalacz stanowy (smoke causes
  activate_alarm) odpala akcje automatycznie, dynamic trigger
  (activate_alarm triggers start_ventilation) odpala kolejna akcje po
  zakonczeniu poprzedniej, warunkowe efekty (causes...if). Smoke trwa
  caly scenariusz, ale dzieki edge-triggered semantyce activate_alarm
  odpala sie tylko raz — w t=0 — a nie cyklicznie.
""")

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

    print_domain(domain)
    print_scenario(scenario)

    if not print_validation(domain, scenario):
        return

    models = solve_and_print(domain, scenario, extra_times=query_times(queries))
    print_queries(queries, models)
